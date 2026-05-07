"""
Flask web application for ADS-B Line of Sight Calculator.
"""

import logging
import argparse
import os
from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
from data_ingester import OpenSkyClient
from distance_calculator import calculate_all_pair_distances, calculate_airport_to_aircraft_distances
from communication_analyzer import count_communication_paths, get_graph_data, calculate_connectivity_metrics_at_range
from los_metrics import calculate_all_los_metrics, calculate_connectivity_curve
from config import (
    CARRIERS,
    REFRESH_INTERVAL_SECONDS,
    DISTANCE_BINS,
    DEFAULT_COMMUNICATION_RANGE_KM,
    TOP_50_AIRPORTS
)
from radio_nets import (
    create_net, update_net, get_net, list_nets, delete_net,
    create_node, update_node, get_node, list_nodes, delete_node,
    get_net_connectivity, get_compliance_status, get_non_compliant_nodes,
)
from satellite_comm import (
    create_satellite, update_satellite, get_satellite, list_satellites, delete_satellite,
    add_planned_usage, list_planned_usage, delete_planned_usage,
    get_nodes_per_satellite, get_satellite_footprints,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global data cache
data_cache = {
    'aircraft_data': [],
    'last_update': None,
    'client': OpenSkyClient()
}


def get_filtered_aircraft(selected_carriers=None):
    """
    Get filtered aircraft list based on carriers.
    
    Args:
        selected_carriers: List of carrier codes
    
    Returns:
        Tuple of (aircraft_list, carrier_ranges_dict)
    """
    all_aircraft = get_cached_aircraft()
    aircraft_list = []
    carrier_ranges = {}
    
    # Filter by carriers
    if selected_carriers:
        aircraft_list.extend([a for a in all_aircraft if a.get('carrier_code') in selected_carriers])
    
    # Remove duplicates by icao24
    seen = set()
    unique_aircraft = []
    for a in aircraft_list:
        icao = a.get('icao24')
        if icao and icao not in seen:
            seen.add(icao)
            unique_aircraft.append(a)
    
    return unique_aircraft, carrier_ranges


def get_cached_aircraft(force_refresh=False):
    """
    Get aircraft data from cache or fetch if stale.
    
    Args:
        force_refresh: If True, force a refresh regardless of cache age
    
    Returns:
        List of aircraft dictionaries
    """
    now = datetime.now()
    
    # Check if cache is valid
    if not force_refresh and data_cache['last_update']:
        age = (now - data_cache['last_update']).total_seconds()
        if age < REFRESH_INTERVAL_SECONDS:
            logger.info(f"Returning cached data (age: {age:.0f}s)")
            return data_cache['aircraft_data']
    
    # Refresh data
    logger.info("Refreshing aircraft data from OpenSky API")
    data_cache['last_update'] = now
    # Note: We'll fetch all data, filtering happens per-request
    data = data_cache['client'].fetch_aircraft_states()
    if data and 'states' in data:
        # Parse all aircraft (filtering by carrier happens in endpoints)
        parsed = []
        for state in data.get('states', []):
            aircraft = data_cache['client'].parse_state_vector(state)
            if aircraft:
                parsed.append(aircraft)
        data_cache['aircraft_data'] = parsed
        logger.info(f"Cached {len(parsed)} aircraft")
        return parsed
    
    # Return stale cache if fetch failed
    return data_cache['aircraft_data']


@app.route('/')
def index():
    """Serve main web interface."""
    return render_template('index.html')


@app.route('/api/aircraft', methods=['GET'])
def get_aircraft():
    """Get all available aircraft data."""
    aircraft = get_cached_aircraft()
    
    # Filter to only top 25 carriers
    carrier_codes = list(CARRIERS.keys())
    filtered = [a for a in aircraft if a.get('carrier_code') in carrier_codes]
    
    return jsonify({
        'aircraft': filtered,
        'last_update': data_cache['last_update'].isoformat() if data_cache['last_update'] else None,
        'total_count': len(filtered)
    })


@app.route('/api/distances', methods=['POST'])
def calculate_distances():
    """
    Calculate distances for selected carriers.
    
    Expected JSON body:
    {
        "carriers": ["DAL", "UAL", "SWA"],
        "carrier_ranges": {"DAL": 200, "UAL": 200},  // optional
        "include_airports": true  // optional, include airport-to-aircraft distances
    }
    """
    try:
        data = request.get_json() or {}
        selected_carriers = data.get('carriers', [])
        include_airports = data.get('include_airports', False)
        
        if not selected_carriers:
            return jsonify({'error': 'No carriers selected'}), 400
        
        # Get carrier-specific ranges
        carrier_ranges = data.get('carrier_ranges', {})
        # Fill in defaults for carriers without specified ranges
        for carrier in selected_carriers:
            if carrier not in carrier_ranges:
                carrier_ranges[carrier] = CARRIERS.get(carrier, {}).get('default_range_km', DEFAULT_COMMUNICATION_RANGE_KM)
        
        # Get and filter aircraft data
        all_aircraft = get_cached_aircraft()
        
        # Filter by carriers
        aircraft_list = []
        if selected_carriers:
            aircraft_list.extend([a for a in all_aircraft if a.get('carrier_code') in selected_carriers])
        
        # Remove duplicates by icao24
        seen = set()
        unique_aircraft = []
        for a in aircraft_list:
            icao = a.get('icao24')
            if icao and icao not in seen:
                seen.add(icao)
                unique_aircraft.append(a)
        aircraft_list = unique_aircraft
        
        # Calculate aircraft-to-aircraft distances
        distances = []
        if len(aircraft_list) >= 2:
            distances = calculate_all_pair_distances(aircraft_list)
        
        # Calculate airport-to-aircraft distances if requested
        airport_distances = []
        if include_airports and len(aircraft_list) > 0:
            airport_distances = calculate_airport_to_aircraft_distances(TOP_50_AIRPORTS, aircraft_list)
        
        # Combine distances for binning
        all_los_distances = [d for d in distances if d.get('los_distance_km') is not None]
        all_los_distances.extend([d for d in airport_distances if d.get('los_distance_km') is not None])
        
        # Bin distances (use los_distance_km for LOS pairs only)
        bin_counts = {}
        for bin_min, bin_max in DISTANCE_BINS:
            bin_key = f"{bin_min}-{bin_max if bin_max != float('inf') else 'inf'}"
            count = sum(1 for d in all_los_distances 
                       if bin_min <= d['los_distance_km'] < bin_max)
            bin_counts[bin_key] = count
        
        return jsonify({
            'distances': distances[:100],  # Limit response size
            'airport_distances': airport_distances[:100] if include_airports else [],
            'aircraft_count': len(aircraft_list),
            'total_pairs': len(distances),
            'total_airport_pairs': len(airport_distances) if include_airports else 0,
            'bins': bin_counts,
            'last_update': data_cache['last_update'].isoformat() if data_cache['last_update'] else None
        })
        
    except Exception as e:
        logger.error(f"Error calculating distances: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/communication', methods=['POST'])
def get_communication_stats():
    """
    Get communication path statistics for selected carriers.
    
    Expected JSON body:
    {
        "carriers": ["DAL", "UAL"],
        "carrier_ranges": {"DAL": 200, "UAL": 200},  // optional
        "include_airports": true  // optional, include airports in connectivity analysis
    }
    """
    try:
        data = request.get_json() or {}
        selected_carriers = data.get('carriers', [])
        include_airports = data.get('include_airports', False)
        
        if not selected_carriers:
            return jsonify({'error': 'No carriers selected'}), 400
        
        # Get carrier-specific ranges
        carrier_ranges = data.get('carrier_ranges', {})
        for carrier in selected_carriers:
            if carrier not in carrier_ranges:
                carrier_ranges[carrier] = CARRIERS.get(carrier, {}).get('default_range_km', DEFAULT_COMMUNICATION_RANGE_KM)
        
        # Get and filter aircraft data
        all_aircraft = get_cached_aircraft()
        
        # Filter by carriers
        aircraft_list = []
        if selected_carriers:
            aircraft_list.extend([a for a in all_aircraft if a.get('carrier_code') in selected_carriers])
        
        # Remove duplicates by icao24
        seen = set()
        unique_aircraft = []
        for a in aircraft_list:
            icao = a.get('icao24')
            if icao and icao not in seen:
                seen.add(icao)
                unique_aircraft.append(a)
        aircraft_list = unique_aircraft
        
        # Calculate aircraft-to-aircraft distances
        distances = []
        if len(aircraft_list) >= 2:
            distances = calculate_all_pair_distances(aircraft_list)
        
        # If airports are included, we need to extend the connectivity graph
        # For now, calculate stats with just aircraft (airports will be included in graph visualization)
        if len(aircraft_list) < 2:
            return jsonify({
                'direct': 0,
                '1hop': 0,
                '2hop': 0,
                '3hop': 0,
                'aircraft_count': len(aircraft_list),
                'airport_count': len(TOP_50_AIRPORTS) if include_airports else 0
            })
        
        # Calculate distances and communication paths
        stats = count_communication_paths(aircraft_list, distances, carrier_ranges)
        
        # Note: Airports are included in graph visualization but not in communication path stats
        # as they are ground stations, not part of the aircraft-to-aircraft communication network
        
        return jsonify({
            **stats,
            'aircraft_count': len(aircraft_list),
            'airport_count': len(TOP_50_AIRPORTS) if include_airports else 0,
            'last_update': data_cache['last_update'].isoformat() if data_cache['last_update'] else None
        })
        
    except Exception as e:
        logger.error(f"Error calculating communication stats: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/carriers', methods=['GET'])
def get_carriers():
    """Get list of available carriers with default ranges."""
    carriers_info = {
        code: {
            'name': info['name'],
            'default_range_km': info['default_range_km']
        }
        for code, info in CARRIERS.items()
    }
    return jsonify(carriers_info)


@app.route('/api/airports', methods=['GET'])
def get_airports():
    """Get list of top 50 airports."""
    airports_info = {
        code: {
            'name': info['name'],
            'latitude': info['latitude'],
            'longitude': info['longitude'],
            'elevation_m': info['elevation_m']
        }
        for code, info in TOP_50_AIRPORTS.items()
    }
    return jsonify(airports_info)


@app.route('/api/los-status', methods=['GET'])
def get_los_status():
    """Get LOS Calculation data availability status."""
    now = datetime.now()
    last_update = data_cache.get('last_update')
    
    # Check if we have recent data and actual aircraft data
    aircraft_count = len(data_cache.get('aircraft_data', []))
    has_data = aircraft_count > 0
    
    if last_update and has_data:
        age_seconds = (now - last_update).total_seconds()
        # Consider data fresh if less than refresh interval + 60 seconds buffer
        is_fresh = age_seconds < (REFRESH_INTERVAL_SECONDS + 60)
        available = is_fresh and has_data
    else:
        age_seconds = None
        available = False
    
    # Check if API client is responding
    api_responding = True
    try:
        # Quick check if client exists and has cached data
        if not data_cache.get('client'):
            api_responding = False
    except Exception:
        api_responding = False
    
    return jsonify({
        'available': available,
        'last_update': last_update.isoformat() if last_update else None,
        'data_age_seconds': age_seconds,
        'api_responding': api_responding,
        'aircraft_count': aircraft_count
    })




@app.route('/api/graph', methods=['POST'])
def api_get_graph():
    """
    Get graph data structure for visualization.
    
    Expected JSON body:
    {
        "carriers": ["DAL", "UAL"],
        "carrier_ranges": {"DAL": 200, "UAL": 200}  // optional
        "include_airports": true  // optional, include airport nodes
    }
    """
    try:
        data = request.get_json() or {}
        selected_carriers = data.get('carriers', [])
        include_airports = data.get('include_airports', False)
        
        if not selected_carriers:
            return jsonify({'error': 'No carriers selected'}), 400
        
        # Get carrier-specific ranges
        carrier_ranges = data.get('carrier_ranges', {})
        for carrier in selected_carriers:
            if carrier not in carrier_ranges:
                carrier_ranges[carrier] = CARRIERS.get(carrier, {}).get('default_range_km', DEFAULT_COMMUNICATION_RANGE_KM)
        
        # Get and filter aircraft data
        all_aircraft = get_cached_aircraft()
        
        # Filter by carriers
        aircraft_list = []
        if selected_carriers:
            aircraft_list.extend([a for a in all_aircraft if a.get('carrier_code') in selected_carriers])
        
        # Remove duplicates by icao24
        seen = set()
        unique_aircraft = []
        for a in aircraft_list:
            icao = a.get('icao24')
            if icao and icao not in seen:
                seen.add(icao)
                unique_aircraft.append(a)
        aircraft_list = unique_aircraft
        
        # Calculate aircraft-to-aircraft distances
        distances = []
        if len(aircraft_list) >= 2:
            distances = calculate_all_pair_distances(aircraft_list)
        
        # Get base graph data
        graph_data = get_graph_data(aircraft_list, distances, carrier_ranges) if len(aircraft_list) >= 1 else {'nodes': [], 'edges': []}
        
        # Add airports if requested
        if include_airports and len(aircraft_list) > 0:
            # Calculate airport-to-aircraft distances
            airport_distances = calculate_airport_to_aircraft_distances(TOP_50_AIRPORTS, aircraft_list)
            
            # Add airport nodes
            for airport_code, airport_info in TOP_50_AIRPORTS.items():
                graph_data['nodes'].append({
                    'id': airport_code,
                    'label': airport_info['name'],
                    'carrier': None,  # Airports don't have carriers
                    'latitude': airport_info['latitude'],
                    'longitude': airport_info['longitude'],
                    'is_airport': True,  # Flag to distinguish airports
                })
            
            # Add airport-to-aircraft edges (within communication range)
            # Use default communication range for airports
            airport_range = DEFAULT_COMMUNICATION_RANGE_KM
            for dist_info in airport_distances:
                airport_code = dist_info['airport']['icao24']
                aircraft_icao = dist_info['aircraft']['icao24']
                distance = dist_info['distance_km']
                
                # Add edge if within communication range
                if distance <= airport_range:
                    graph_data['edges'].append({
                        'from': airport_code,
                        'to': aircraft_icao,
                        'distance': distance,
                    })
        
        return jsonify({
            **graph_data,
            'aircraft_count': len(aircraft_list),
            'airport_count': len(TOP_50_AIRPORTS) if include_airports else 0,
            'last_update': data_cache['last_update'].isoformat() if data_cache['last_update'] else None
        })
        
    except Exception as e:
        logger.error(f"Error getting graph data: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/los-metrics', methods=['POST'])
def get_los_metrics():
    """
    Get comprehensive LOS metrics for selected carriers and/or military groups.
    
    Expected JSON body:
    {
        "carriers": ["DAL", "UAL"],
        "carrier_ranges": {"DAL": 200, "UAL": 200}  // optional
    }
    """
    try:
        data = request.get_json() or {}
        selected_carriers = data.get('carriers', [])
        
        if not selected_carriers:
            return jsonify({'error': 'No carriers selected'}), 400
        
        # Get carrier-specific ranges
        carrier_ranges = data.get('carrier_ranges', {})
        for carrier in selected_carriers:
            if carrier not in carrier_ranges:
                carrier_ranges[carrier] = CARRIERS.get(carrier, {}).get('default_range_km', DEFAULT_COMMUNICATION_RANGE_KM)
        
        # Get and filter aircraft data
        aircraft_list, _ = get_filtered_aircraft(selected_carriers)
        
        if len(aircraft_list) < 1:
            return jsonify({
                'coverage': {
                    'total_pairs': 0,
                    'los_pairs_count': 0,
                    'los_pairs_percentage': 0,
                    'average_los_distance_km': 0,
                    'min_los_distance_km': 0,
                    'max_los_distance_km': 0,
                    'median_los_distance_km': 0,
                    'los_distance_std_dev_km': 0,
                },
                'connectivity': {
                    'graph_density': 0,
                    'average_node_degree': 0,
                    'clustering_coefficient': 0,
                    'connected_components_count': 0,
                    'largest_component_size': 0,
                    'average_path_length': 0,
                },
                'geographic': {
                    'los_pairs_count': 0,
                    'bounding_box': None,
                    'average_altitude_km': 0,
                    'average_altitude_diff_km': 0,
                    'altitude_distribution': {
                        'low_band_count': 0,
                        'medium_band_count': 0,
                        'high_band_count': 0,
                    }
                },
                'aircraft_count': 0
            })
        
        # Calculate distances and LOS metrics
        distances = calculate_all_pair_distances(aircraft_list)
        metrics = calculate_all_los_metrics(aircraft_list, distances, carrier_ranges)
        
        return jsonify({
            **metrics,
            'aircraft_count': len(aircraft_list),
            'last_update': data_cache['last_update'].isoformat() if data_cache['last_update'] else None
        })
        
    except Exception as e:
        logger.error(f"Error calculating LOS metrics: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/connectivity-curve', methods=['POST'])
def get_connectivity_curve():
    """
    Get connectivity curve data to identify the "knee in the curve" for multi-hop solutions.
    
    Expected JSON body:
    {
        "carriers": ["DAL", "UAL"],
        "carrier_ranges": {"DAL": 200, "UAL": 200}  // optional
    }
    """
    try:
        data = request.get_json() or {}
        selected_carriers = data.get('carriers', [])
        
        if not selected_carriers:
            return jsonify({'error': 'No carriers selected'}), 400
        
        # Get carrier-specific ranges
        carrier_ranges = data.get('carrier_ranges', {})
        for carrier in selected_carriers:
            if carrier not in carrier_ranges:
                carrier_ranges[carrier] = CARRIERS.get(carrier, {}).get('default_range_km', DEFAULT_COMMUNICATION_RANGE_KM)
        
        # Get and filter aircraft data
        aircraft_list, _ = get_filtered_aircraft(selected_carriers)
        
        if len(aircraft_list) < 2:
            return jsonify({
                'cumulative_pairs': {'direct': 0, '1hop': 0, '2hop': 0, '3hop': 0, '4hop': 0, '5hop': 0},
                'marginal_improvement': {'1hop': 0, '2hop': 0, '3hop': 0, '4hop': 0, '5hop': 0},
                'knee_hop': None,
                'total_aircraft': len(aircraft_list),
                'max_possible_pairs': 0
            })
        
        # Calculate distances and connectivity curve
        distances = calculate_all_pair_distances(aircraft_list)
        curve_data = calculate_connectivity_curve(aircraft_list, distances, carrier_ranges)
        
        return jsonify({
            **curve_data,
            'last_update': data_cache['last_update'].isoformat() if data_cache['last_update'] else None
        })
        
    except Exception as e:
        logger.error(f"Error calculating connectivity curve: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/range-sensitivity', methods=['POST'])
def get_range_sensitivity():
    """
    Calculate connectivity metrics at multiple range thresholds to show sensitivity.
    
    Expected JSON body:
    {
        "carriers": ["DAL", "UAL"],
        "carrier_ranges": {"DAL": 200, "UAL": 200}  // optional, for reference only
    }
    
    Returns:
    {
        "sensitivity_data": [
            {
                "range_km": 50,
                "direct_connections": 10,
                "total_reachable_pairs": 45,
                "graph_density": 0.1,
                "average_degree": 2.5
            },
            ...
        ],
        "current_ranges": {"DAL": 200, "UAL": 200, "US_MIL": 200}  // current ranges for reference
    }
    """
    try:
        data = request.get_json() or {}
        selected_carriers = data.get('carriers', [])
        
        if not selected_carriers:
            return jsonify({'error': 'No carriers selected'}), 400
        
        # Get current carrier ranges for reference
        carrier_ranges = data.get('carrier_ranges', {})
        for carrier in selected_carriers:
            if carrier not in carrier_ranges:
                carrier_ranges[carrier] = CARRIERS.get(carrier, {}).get('default_range_km', DEFAULT_COMMUNICATION_RANGE_KM)
        
        # Current ranges for return
        current_ranges = carrier_ranges.copy()
        
        # Get and filter aircraft data
        aircraft_list, _ = get_filtered_aircraft(selected_carriers)
        
        if len(aircraft_list) < 2:
            return jsonify({
                'sensitivity_data': [],
                'current_ranges': carrier_ranges,
                'aircraft_count': len(aircraft_list)
            })
        
        # Calculate distances once (they don't change with range)
        distances = calculate_all_pair_distances(aircraft_list)
        
        # Test multiple range thresholds (50km to 400km in 50km steps)
        range_thresholds = list(range(50, 451, 50))  # 50, 100, 150, ..., 400
        sensitivity_data = []
        
        for test_range in range_thresholds:
            metrics = calculate_connectivity_metrics_at_range(
                aircraft_list, 
                distances, 
                test_range
            )
            sensitivity_data.append({
                'range_km': test_range,
                **metrics
            })
        
        return jsonify({
            'sensitivity_data': sensitivity_data,
            'current_ranges': carrier_ranges,
            'aircraft_count': len(aircraft_list),
            'last_update': data_cache['last_update'].isoformat() if data_cache['last_update'] else None
        })
        
    except Exception as e:
        logger.error(f"Error calculating range sensitivity: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# --- Radio Net Configuration API ---

@app.route('/api/radio-nets', methods=['GET'])
def api_list_nets():
    """List all radio nets."""
    nets = list_nets()
    return jsonify({'nets': nets})


@app.route('/api/radio-nets', methods=['POST'])
def api_create_net():
    """Create a radio net. Body: {name, frequency_mhz, band?, description?}."""
    data = request.get_json() or {}
    name = data.get('name')
    frequency_mhz = data.get('frequency_mhz')
    if not name or frequency_mhz is None:
        return jsonify({'error': 'name and frequency_mhz required'}), 400
    try:
        frequency_mhz = float(frequency_mhz)
    except (ValueError, TypeError):
        return jsonify({'error': 'frequency_mhz must be numeric'}), 400
    net = create_net(
        name=str(name),
        frequency_mhz=frequency_mhz,
        band=str(data.get('band', 'VHF')),
        description=str(data.get('description', '')),
    )
    return jsonify(net), 201


@app.route('/api/radio-nets/<net_id>', methods=['GET'])
def api_get_net(net_id):
    """Get a radio net by ID."""
    net = get_net(net_id)
    if not net:
        return jsonify({'error': 'Net not found'}), 404
    return jsonify(net)


@app.route('/api/radio-nets/<net_id>', methods=['PUT'])
def api_update_net(net_id):
    """Update a radio net. Body: {name?, frequency_mhz?, band?, description?}."""
    data = request.get_json() or {}
    allowed = {k: data[k] for k in ('name', 'frequency_mhz', 'band', 'description') if k in data}
    net = update_net(net_id, **allowed)
    if not net:
        return jsonify({'error': 'Net not found'}), 404
    return jsonify(net)


@app.route('/api/radio-nets/<net_id>', methods=['DELETE'])
def api_delete_net(net_id):
    """Delete a radio net."""
    if not delete_net(net_id):
        return jsonify({'error': 'Net not found'}), 404
    return jsonify({'deleted': net_id})


@app.route('/api/radio-nodes', methods=['GET'])
def api_list_nodes():
    """List all radio nodes."""
    nodes = list_nodes()
    return jsonify({'nodes': nodes})


@app.route('/api/radio-nodes', methods=['POST'])
def api_create_node():
    """Create a radio node. Body: {label, configured_nets?, assigned_nets?, frequency_capability?}."""
    data = request.get_json() or {}
    label = data.get('label', '')
    node = create_node(
        label=str(label),
        configured_nets=data.get('configured_nets', []),
        assigned_nets=data.get('assigned_nets', []),
        frequency_capability=data.get('frequency_capability', []),
    )
    return jsonify(node), 201


@app.route('/api/radio-nodes/<node_id>', methods=['GET'])
def api_get_node(node_id):
    """Get a radio node by ID."""
    node = get_node(node_id)
    if not node:
        return jsonify({'error': 'Node not found'}), 404
    return jsonify(node)


@app.route('/api/radio-nodes/<node_id>', methods=['PUT'])
def api_update_node(node_id):
    """Update a radio node. Body: {label?, configured_nets?, assigned_nets?, frequency_capability?}."""
    data = request.get_json() or {}
    allowed = {k: data[k] for k in ('label', 'configured_nets', 'assigned_nets', 'frequency_capability') if k in data}
    node = update_node(node_id, **allowed)
    if not node:
        return jsonify({'error': 'Node not found'}), 404
    return jsonify(node)


@app.route('/api/radio-nodes/<node_id>', methods=['DELETE'])
def api_delete_node(node_id):
    """Delete a radio node."""
    if not delete_node(node_id):
        return jsonify({'error': 'Node not found'}), 404
    return jsonify({'deleted': node_id})


@app.route('/api/radio-nets/connectivity', methods=['GET'])
def api_net_connectivity():
    """Get net connectivity: which nets are connected, bridge nodes, connected groups."""
    return jsonify(get_net_connectivity())


@app.route('/api/radio-nets/compliance', methods=['GET'])
def api_compliance_status():
    """Get compliance status per net and per node."""
    return jsonify(get_compliance_status())


@app.route('/api/radio-nets/non-compliant', methods=['GET'])
def api_non_compliant_nodes():
    """List radios not set up to join their assigned nets."""
    return jsonify({'non_compliant': get_non_compliant_nodes()})


# --- Satellite Communications API ---

@app.route('/api/satellites', methods=['GET'])
def api_list_satellites():
    """List all satellites."""
    return jsonify({'satellites': list_satellites()})


@app.route('/api/satellites', methods=['POST'])
def api_create_satellite():
    """Create a satellite. Body: {name, footprint_center_lat, footprint_center_lon, footprint_radius_km}."""
    data = request.get_json() or {}
    name = data.get('name')
    lat = data.get('footprint_center_lat')
    lon = data.get('footprint_center_lon')
    radius = data.get('footprint_radius_km')
    if not name or lat is None or lon is None or radius is None:
        return jsonify({'error': 'name, footprint_center_lat, footprint_center_lon, footprint_radius_km required'}), 400
    try:
        lat = float(lat)
        lon = float(lon)
        radius = float(radius)
    except (ValueError, TypeError):
        return jsonify({'error': 'footprint fields must be numeric'}), 400
    sat = create_satellite(name=str(name), footprint_center_lat=lat, footprint_center_lon=lon, footprint_radius_km=radius)
    return jsonify(sat), 201


@app.route('/api/satellites/<sat_id>', methods=['GET'])
def api_get_satellite(sat_id):
    """Get a satellite by ID."""
    sat = get_satellite(sat_id)
    if not sat:
        return jsonify({'error': 'Satellite not found'}), 404
    return jsonify(sat)


@app.route('/api/satellites/<sat_id>', methods=['PUT'])
def api_update_satellite(sat_id):
    """Update a satellite."""
    data = request.get_json() or {}
    allowed = {k: data[k] for k in ('name', 'footprint_center_lat', 'footprint_center_lon', 'footprint_radius_km') if k in data}
    sat = update_satellite(sat_id, **allowed)
    if not sat:
        return jsonify({'error': 'Satellite not found'}), 404
    return jsonify(sat)


@app.route('/api/satellites/<sat_id>', methods=['DELETE'])
def api_delete_satellite(sat_id):
    """Delete a satellite."""
    if not delete_satellite(sat_id):
        return jsonify({'error': 'Satellite not found'}), 404
    return jsonify({'deleted': sat_id})


@app.route('/api/satellites/footprints', methods=['GET'])
def api_satellite_footprints():
    """Get satellite footprints for map layer."""
    return jsonify({'footprints': get_satellite_footprints()})


@app.route('/api/satellites/planned-usage', methods=['GET'])
def api_list_planned_usage():
    """List planned usage. Query params: node_id?, satellite_id?"""
    node_id = request.args.get('node_id')
    satellite_id = request.args.get('satellite_id')
    usage = list_planned_usage(node_id=node_id or None, satellite_id=satellite_id or None)
    return jsonify({'planned_usage': usage})


@app.route('/api/satellites/planned-usage', methods=['POST'])
def api_add_planned_usage():
    """Add planned usage. Body: {node_id, satellite_id, start_time, end_time}."""
    data = request.get_json() or {}
    node_id = data.get('node_id')
    satellite_id = data.get('satellite_id')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    if not all([node_id, satellite_id, start_time, end_time]):
        return jsonify({'error': 'node_id, satellite_id, start_time, end_time required'}), 400
    usage = add_planned_usage(node_id, satellite_id, start_time, end_time)
    if not usage:
        return jsonify({'error': 'Satellite not found'}), 404
    return jsonify(usage), 201


@app.route('/api/satellites/planned-usage/<usage_id>', methods=['DELETE'])
def api_delete_planned_usage(usage_id):
    """Delete a planned usage."""
    if not delete_planned_usage(usage_id):
        return jsonify({'error': 'Planned usage not found'}), 404
    return jsonify({'deleted': usage_id})


@app.route('/api/satellites/nodes-per-satellite', methods=['GET'])
def api_nodes_per_satellite():
    """Get node counts per satellite. Query params: time?, saturation_threshold?"""
    query_time = request.args.get('time')
    try:
        threshold = int(request.args.get('saturation_threshold', 10))
    except (ValueError, TypeError):
        threshold = 10
    return jsonify(get_nodes_per_satellite(query_time=query_time, saturation_threshold=threshold))


@app.route('/api/los-table', methods=['POST'])
def get_los_table():
    """
    Get full LOS pair data for a sortable/filterable data table.

    Expected JSON body:
    {
        "carriers": ["DAL", "UAL"],
        "carrier_ranges": {"DAL": 200, "UAL": 200},
        "include_airports": true
    }
    """
    try:
        data = request.get_json() or {}
        selected_carriers = data.get('carriers', [])
        include_airports = data.get('include_airports', False)

        if not selected_carriers:
            return jsonify({'error': 'No carriers selected'}), 400

        carrier_ranges = data.get('carrier_ranges', {})
        for carrier in selected_carriers:
            if carrier not in carrier_ranges:
                carrier_ranges[carrier] = CARRIERS.get(carrier, {}).get(
                    'default_range_km', DEFAULT_COMMUNICATION_RANGE_KM
                )

        all_aircraft = get_cached_aircraft()
        aircraft_list = [a for a in all_aircraft if a.get('carrier_code') in selected_carriers]

        seen = set()
        unique_aircraft = []
        for a in aircraft_list:
            icao = a.get('icao24')
            if icao and icao not in seen:
                seen.add(icao)
                unique_aircraft.append(a)
        aircraft_list = unique_aircraft

        aircraft_by_icao = {a['icao24']: a for a in aircraft_list}

        pairs = []

        if len(aircraft_list) >= 2:
            distances = calculate_all_pair_distances(aircraft_list)
            for d in distances:
                ac1 = aircraft_by_icao.get(d['aircraft1']['icao24'], {})
                ac2 = aircraft_by_icao.get(d['aircraft2']['icao24'], {})
                pairs.append({
                    'aircraft1_icao24': d['aircraft1']['icao24'],
                    'aircraft1_callsign': d['aircraft1'].get('callsign') or d['aircraft1']['icao24'],
                    'aircraft1_carrier': d['aircraft1'].get('carrier') or '',
                    'aircraft1_altitude': ac1.get('geo_altitude') or 0,
                    'aircraft2_icao24': d['aircraft2']['icao24'],
                    'aircraft2_callsign': d['aircraft2'].get('callsign') or d['aircraft2']['icao24'],
                    'aircraft2_carrier': d['aircraft2'].get('carrier') or '',
                    'aircraft2_altitude': ac2.get('geo_altitude') or 0,
                    'distance_km': round(d['distance_km'], 2),
                    'radio_horizon_km': round(d['radio_horizon_km'], 2),
                    'los_distance_km': round(d['los_distance_km'], 2) if d['los_distance_km'] is not None else None,
                    'within_los': d['within_los'],
                })

        if include_airports and len(aircraft_list) > 0:
            airport_distances = calculate_airport_to_aircraft_distances(TOP_50_AIRPORTS, aircraft_list)
            for d in airport_distances:
                ac = aircraft_by_icao.get(d['aircraft']['icao24'], {})
                pairs.append({
                    'aircraft1_icao24': d['airport']['icao24'],
                    'aircraft1_callsign': d['airport'].get('name') or d['airport']['icao24'],
                    'aircraft1_carrier': 'AIRPORT',
                    'aircraft1_altitude': d['airport'].get('elevation_m') or 0,
                    'aircraft2_icao24': d['aircraft']['icao24'],
                    'aircraft2_callsign': d['aircraft'].get('callsign') or d['aircraft']['icao24'],
                    'aircraft2_carrier': d['aircraft'].get('carrier') or '',
                    'aircraft2_altitude': ac.get('geo_altitude') or 0,
                    'distance_km': round(d['distance_km'], 2),
                    'radio_horizon_km': round(d['radio_horizon_km'], 2),
                    'los_distance_km': round(d['los_distance_km'], 2) if d['los_distance_km'] is not None else None,
                    'within_los': d['within_los'],
                })

        return jsonify({
            'pairs': pairs,
            'total_count': len(pairs),
            'aircraft_count': len(aircraft_list),
            'last_update': data_cache['last_update'].isoformat() if data_cache['last_update'] else None,
        })

    except Exception as e:
        logger.error(f"Error getting LOS table data: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ADS-B Line of Sight Calculator')
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port to bind to (default: 5000)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    args = parser.parse_args()
    
    app.run(debug=args.debug, host=args.host, port=args.port)

