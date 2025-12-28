"""
Flask web application for ADS-B Line of Sight Calculator.
"""

import logging
from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
from data_ingester import OpenSkyClient
from distance_calculator import calculate_all_pair_distances
from communication_analyzer import count_communication_paths, get_graph_data
from config import (
    CARRIERS, 
    REFRESH_INTERVAL_SECONDS,
    DISTANCE_BINS,
    DEFAULT_COMMUNICATION_RANGE_KM
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
        "carrier_ranges": {"DAL": 200, "UAL": 200}  // optional, uses defaults if not provided
    }
    """
    try:
        data = request.get_json() or {}
        selected_carriers = data.get('carriers', [])
        
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
        aircraft_list = [a for a in all_aircraft if a.get('carrier_code') in selected_carriers]
        
        if len(aircraft_list) < 2:
            return jsonify({
                'distances': [],
                'aircraft_count': len(aircraft_list),
                'bins': {f"{bin_min}-{bin_max if bin_max != float('inf') else 'inf'}": 0 
                        for bin_min, bin_max in DISTANCE_BINS}
            })
        
        # Calculate distances
        distances = calculate_all_pair_distances(aircraft_list)
        
        # Bin distances (use distance_km for all pairs, los_distance_km for LOS pairs only)
        bin_counts = {}
        for bin_min, bin_max in DISTANCE_BINS:
            bin_key = f"{bin_min}-{bin_max if bin_max != float('inf') else 'inf'}"
            count = sum(1 for d in distances 
                       if d['los_distance_km'] is not None and bin_min <= d['los_distance_km'] < bin_max)
            bin_counts[bin_key] = count
        
        return jsonify({
            'distances': distances[:100],  # Limit response size
            'aircraft_count': len(aircraft_list),
            'total_pairs': len(distances),
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
        all_aircraft = get_cached_aircraft()
        aircraft_list = [a for a in all_aircraft if a.get('carrier_code') in selected_carriers]
        
        if len(aircraft_list) < 2:
            return jsonify({
                'direct': 0,
                '1hop': 0,
                '2hop': 0,
                '3hop': 0,
                'aircraft_count': len(aircraft_list)
            })
        
        # Calculate distances and communication paths
        distances = calculate_all_pair_distances(aircraft_list)
        stats = count_communication_paths(aircraft_list, distances, carrier_ranges)
        
        return jsonify({
            **stats,
            'aircraft_count': len(aircraft_list),
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


@app.route('/api/graph', methods=['POST'])
def api_get_graph():
    """
    Get graph data structure for visualization.
    
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
        all_aircraft = get_cached_aircraft()
        aircraft_list = [a for a in all_aircraft if a.get('carrier_code') in selected_carriers]
        
        if len(aircraft_list) < 1:
            return jsonify({
                'nodes': [],
                'edges': [],
                'aircraft_count': 0
            })
        
        # Calculate distances and get graph data
        distances = calculate_all_pair_distances(aircraft_list)
        graph_data = get_graph_data(aircraft_list, distances, carrier_ranges)
        
        return jsonify({
            **graph_data,
            'aircraft_count': len(aircraft_list),
            'last_update': data_cache['last_update'].isoformat() if data_cache['last_update'] else None
        })
        
    except Exception as e:
        logger.error(f"Error getting graph data: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

