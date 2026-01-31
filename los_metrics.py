"""
Line-of-sight metrics calculation for coverage, connectivity, and geographic analysis.
"""

import math
import statistics
from typing import Dict, List, Set, Tuple
from collections import defaultdict, deque
from communication_analyzer import build_connectivity_graph, bfs_with_depth_limit


def calculate_los_coverage_metrics(distances: List[Dict]) -> Dict:
    """
    Calculate LOS coverage statistics.
    
    Args:
        distances: List of distance calculations with los_distance_km and within_los fields
    
    Returns:
        Dictionary with coverage metrics
    """
    total_pairs = len(distances)
    los_pairs = [d for d in distances if d.get('within_los', False)]
    los_distances = [d['los_distance_km'] for d in los_pairs if d.get('los_distance_km') is not None]
    
    los_count = len(los_pairs)
    los_percentage = (los_count / total_pairs * 100) if total_pairs > 0 else 0
    
    if los_distances:
        avg_los_distance = statistics.mean(los_distances)
        min_los_distance = min(los_distances)
        max_los_distance = max(los_distances)
        median_los_distance = statistics.median(los_distances)
        std_los_distance = statistics.stdev(los_distances) if len(los_distances) > 1 else 0
    else:
        avg_los_distance = 0
        min_los_distance = 0
        max_los_distance = 0
        median_los_distance = 0
        std_los_distance = 0
    
    return {
        'total_pairs': total_pairs,
        'los_pairs_count': los_count,
        'los_pairs_percentage': round(los_percentage, 2),
        'average_los_distance_km': round(avg_los_distance, 2),
        'min_los_distance_km': round(min_los_distance, 2),
        'max_los_distance_km': round(max_los_distance, 2),
        'median_los_distance_km': round(median_los_distance, 2),
        'los_distance_std_dev_km': round(std_los_distance, 2),
    }


def calculate_local_clustering_coefficient(graph: Dict[str, Set[str]], node: str) -> float:
    """
    Calculate local clustering coefficient for a node.
    
    Args:
        graph: Adjacency list representation
        node: Node to calculate clustering for
    
    Returns:
        Clustering coefficient (0-1)
    """
    neighbors = graph.get(node, set())
    if len(neighbors) < 2:
        return 0.0
    
    # Count edges between neighbors
    edges_between_neighbors = 0
    neighbor_list = list(neighbors)
    for i in range(len(neighbor_list)):
        for j in range(i + 1, len(neighbor_list)):
            if neighbor_list[j] in graph.get(neighbor_list[i], set()):
                edges_between_neighbors += 1
    
    # Maximum possible edges between neighbors
    max_possible = len(neighbors) * (len(neighbors) - 1) / 2
    
    return edges_between_neighbors / max_possible if max_possible > 0 else 0.0


def find_connected_components(graph: Dict[str, Set[str]], all_nodes: Set[str]) -> List[Set[str]]:
    """
    Find all connected components in the graph.
    
    Args:
        graph: Adjacency list representation
        all_nodes: Set of all node IDs
    
    Returns:
        List of sets, each containing nodes in a connected component
    """
    visited = set()
    components = []
    
    for node in all_nodes:
        if node in visited:
            continue
        
        # BFS to find component
        component = set()
        queue = deque([node])
        visited.add(node)
        
        while queue:
            current = queue.popleft()
            component.add(current)
            
            for neighbor in graph.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        if component:
            components.append(component)
    
    return components


def calculate_average_path_length(graph: Dict[str, Set[str]], nodes: Set[str]) -> float:
    """
    Calculate average shortest path length for connected pairs.
    
    Args:
        graph: Adjacency list representation
        nodes: Set of all node IDs
    
    Returns:
        Average path length (or 0 if no connected pairs)
    """
    path_lengths = []
    node_list = list(nodes)
    
    for i in range(len(node_list)):
        start = node_list[i]
        if start not in graph:
            continue
        
        # BFS to find shortest paths
        distances = {start: 0}
        queue = deque([start])
        
        while queue:
            current = queue.popleft()
            for neighbor in graph.get(current, set()):
                if neighbor not in distances:
                    distances[neighbor] = distances[current] + 1
                    queue.append(neighbor)
        
        # Add path lengths to other nodes
        for target in distances:
            if target != start and distances[target] > 0:
                path_lengths.append(distances[target])
    
    return statistics.mean(path_lengths) if path_lengths else 0.0


def calculate_los_connectivity_metrics(aircraft_list: List[Dict],
                                     distances: List[Dict],
                                     carrier_ranges: Dict[str, float]) -> Dict:
    """
    Calculate graph-based connectivity metrics.
    
    Args:
        aircraft_list: List of aircraft dictionaries
        distances: List of distance calculations
        carrier_ranges: Dictionary mapping carrier codes to communication range (km)
    
    Returns:
        Dictionary with connectivity metrics
    """
    graph = build_connectivity_graph(aircraft_list, distances, carrier_ranges)
    all_nodes = {a['icao24'] for a in aircraft_list}
    
    # Graph density
    num_nodes = len(all_nodes)
    num_edges = sum(len(neighbors) for neighbors in graph.values()) // 2  # Undirected graph
    max_possible_edges = num_nodes * (num_nodes - 1) / 2 if num_nodes > 1 else 0
    graph_density = (num_edges / max_possible_edges) if max_possible_edges > 0 else 0
    
    # Average node degree
    degrees = [len(graph.get(node, set())) for node in all_nodes]
    avg_degree = statistics.mean(degrees) if degrees else 0
    
    # Clustering coefficient (average local clustering)
    clustering_coeffs = []
    for node in all_nodes:
        if node in graph:
            coeff = calculate_local_clustering_coefficient(graph, node)
            clustering_coeffs.append(coeff)
    avg_clustering = statistics.mean(clustering_coeffs) if clustering_coeffs else 0
    
    # Connected components
    components = find_connected_components(graph, all_nodes)
    num_components = len(components)
    largest_component_size = max(len(c) for c in components) if components else 0
    
    # Average path length (only for largest component if it exists)
    avg_path_length = 0.0
    if components:
        largest_component = max(components, key=len)
        if len(largest_component) > 1:
            # Create subgraph for largest component
            subgraph = {node: graph.get(node, set()) & largest_component for node in largest_component}
            avg_path_length = calculate_average_path_length(subgraph, largest_component)
    
    return {
        'graph_density': round(graph_density, 4),
        'average_node_degree': round(avg_degree, 2),
        'clustering_coefficient': round(avg_clustering, 4),
        'connected_components_count': num_components,
        'largest_component_size': largest_component_size,
        'average_path_length': round(avg_path_length, 2),
    }


def calculate_los_geographic_metrics(aircraft_list: List[Dict],
                                    distances: List[Dict]) -> Dict:
    """
    Calculate geographic distribution metrics for LOS pairs.
    
    Args:
        aircraft_list: List of aircraft dictionaries
        distances: List of distance calculations
    
    Returns:
        Dictionary with geographic metrics
    """
    # Filter to LOS pairs only
    los_pairs = [d for d in distances if d.get('within_los', False)]
    
    if not los_pairs:
        return {
            'los_pairs_count': 0,
            'bounding_box': None,
            'average_altitude_km': 0,
            'average_altitude_diff_km': 0,
            'altitude_distribution': {
                'low_band_count': 0,
                'medium_band_count': 0,
                'high_band_count': 0,
            }
        }
    
    # Create mapping from icao24 to aircraft data
    aircraft_by_icao = {a['icao24']: a for a in aircraft_list}
    
    # Collect coordinates and altitudes for LOS pairs
    lats = []
    lons = []
    altitudes = []
    altitude_diffs = []
    
    for pair in los_pairs:
        icao1 = pair['aircraft1']['icao24']
        icao2 = pair['aircraft2']['icao24']
        
        ac1 = aircraft_by_icao.get(icao1)
        ac2 = aircraft_by_icao.get(icao2)
        
        if ac1 and ac2:
            if ac1.get('latitude') is not None and ac1.get('longitude') is not None:
                lats.append(ac1['latitude'])
                lons.append(ac1['longitude'])
            if ac2.get('latitude') is not None and ac2.get('longitude') is not None:
                lats.append(ac2['latitude'])
                lons.append(ac2['longitude'])
            
            alt1 = (ac1.get('geo_altitude', 0) or 0) / 1000.0  # Convert to km
            alt2 = (ac2.get('geo_altitude', 0) or 0) / 1000.0
            altitudes.extend([alt1, alt2])
            altitude_diffs.append(abs(alt1 - alt2))
    
    # Bounding box
    bounding_box = None
    if lats and lons:
        bounding_box = {
            'min_latitude': round(min(lats), 4),
            'max_latitude': round(max(lats), 4),
            'min_longitude': round(min(lons), 4),
            'max_longitude': round(max(lons), 4),
        }
    
    # Altitude statistics
    avg_altitude = statistics.mean(altitudes) if altitudes else 0
    avg_altitude_diff = statistics.mean(altitude_diffs) if altitude_diffs else 0
    
    # Altitude-based zones (low: 0-6km, medium: 6-12km, high: 12km+)
    low_band = sum(1 for alt in altitudes if 0 <= alt < 6)
    medium_band = sum(1 for alt in altitudes if 6 <= alt < 12)
    high_band = sum(1 for alt in altitudes if alt >= 12)
    
    return {
        'los_pairs_count': len(los_pairs),
        'bounding_box': bounding_box,
        'average_altitude_km': round(avg_altitude, 2),
        'average_altitude_diff_km': round(avg_altitude_diff, 2),
        'altitude_distribution': {
            'low_band_count': low_band,
            'medium_band_count': medium_band,
            'high_band_count': high_band,
        }
    }


def calculate_hub_metrics(aircraft_list: List[Dict],
                          distances: List[Dict],
                          carrier_ranges: Dict[str, float]) -> Dict:
    """
    Calculate hub metrics to identify potential carrier hubs with LOS capabilities.
    
    Args:
        aircraft_list: List of aircraft dictionaries
        distances: List of distance calculations
        carrier_ranges: Dictionary mapping carrier codes to communication range (km)
    
    Returns:
        Dictionary with hub analysis including top hubs by degree and centrality
    """
    graph = build_connectivity_graph(aircraft_list, distances, carrier_ranges)
    aircraft_by_icao = {a['icao24']: a for a in aircraft_list}
    
    # Calculate degree (number of connections) for each aircraft
    hub_scores = []
    for aircraft in aircraft_list:
        icao = aircraft['icao24']
        degree = len(graph.get(icao, set()))
        
        # Calculate reachability at different hop levels
        reachable_1hop = len(bfs_with_depth_limit(graph, icao, max_depth=2))
        reachable_2hop = len(bfs_with_depth_limit(graph, icao, max_depth=3))
        reachable_3hop = len(bfs_with_depth_limit(graph, icao, max_depth=4))
        
        # Hub score: combination of degree and multi-hop reachability
        hub_score = degree * 2 + reachable_1hop + (reachable_2hop * 0.5) + (reachable_3hop * 0.25)
        
        hub_scores.append({
            'icao24': icao,
            'callsign': aircraft.get('callsign') or icao,
            'carrier': aircraft.get('carrier_code', ''),
            'degree': degree,
            'reachable_1hop': reachable_1hop,
            'reachable_2hop': reachable_2hop,
            'reachable_3hop': reachable_3hop,
            'hub_score': hub_score
        })
    
    # Sort by hub score
    hub_scores.sort(key=lambda x: x['hub_score'], reverse=True)
    
    # Get top 20 hubs
    top_hubs = hub_scores[:20]
    
    # Calculate carrier-level hub statistics
    carrier_hub_stats = defaultdict(lambda: {
        'total_aircraft': 0, 
        'total_degree': 0, 
        'total_hub_score': 0,
        'avg_degree': 0, 
        'avg_hub_score': 0,
        'max_degree': 0,
        'max_hub_score': 0
    })
    for hub in hub_scores:
        carrier = hub['carrier']
        if carrier:
            carrier_hub_stats[carrier]['total_aircraft'] += 1
            carrier_hub_stats[carrier]['total_degree'] += hub['degree']
            carrier_hub_stats[carrier]['total_hub_score'] += hub['hub_score']
            carrier_hub_stats[carrier]['max_degree'] = max(carrier_hub_stats[carrier]['max_degree'], hub['degree'])
            carrier_hub_stats[carrier]['max_hub_score'] = max(carrier_hub_stats[carrier]['max_hub_score'], hub['hub_score'])
    
    for carrier in carrier_hub_stats:
        stats = carrier_hub_stats[carrier]
        if stats['total_aircraft'] > 0:
            stats['avg_degree'] = stats['total_degree'] / stats['total_aircraft']
            stats['avg_hub_score'] = stats['total_hub_score'] / stats['total_aircraft']
    
    return {
        'top_hubs': top_hubs,
        'carrier_stats': dict(carrier_hub_stats),
        'total_aircraft': len(aircraft_list)
    }


def calculate_connectivity_curve(aircraft_list: List[Dict],
                                 distances: List[Dict],
                                 carrier_ranges: Dict[str, float]) -> Dict:
    """
    Calculate connectivity curve data to identify the "knee in the curve".
    Shows how connectivity improves with additional hops.
    
    Args:
        aircraft_list: List of aircraft dictionaries
        distances: List of distance calculations
        carrier_ranges: Dictionary mapping carrier codes to communication range (km)
    
    Returns:
        Dictionary with connectivity curve data for plotting
    """
    graph = build_connectivity_graph(aircraft_list, distances, carrier_ranges)
    
    # Calculate unique pairs at each hop level (similar to count_communication_paths)
    direct_pairs = set()
    hop1_pairs = set()
    hop2_pairs = set()
    hop3_pairs = set()
    hop4_pairs = set()
    hop5_pairs = set()
    
    for aircraft in aircraft_list:
        icao = aircraft['icao24']
        direct_neighbors = graph.get(icao, set())
        
        # Direct connections
        for neighbor in direct_neighbors:
            pair = tuple(sorted([icao, neighbor]))
            direct_pairs.add(pair)
        
        # 1-hop (depth 2: start -> intermediate -> target)
        hop1_reachable = bfs_with_depth_limit(graph, icao, max_depth=2)
        for target in hop1_reachable:
            if target not in direct_neighbors:
                pair = tuple(sorted([icao, target]))
                hop1_pairs.add(pair)
        
        # 2-hop (depth 3)
        hop2_reachable = bfs_with_depth_limit(graph, icao, max_depth=3)
        for target in hop2_reachable:
            if target not in direct_neighbors and target not in hop1_reachable:
                pair = tuple(sorted([icao, target]))
                hop2_pairs.add(pair)
        
        # 3-hop (depth 4)
        hop3_reachable = bfs_with_depth_limit(graph, icao, max_depth=4)
        for target in hop3_reachable:
            if target not in direct_neighbors and target not in hop1_reachable and target not in hop2_reachable:
                pair = tuple(sorted([icao, target]))
                hop3_pairs.add(pair)
        
        # 4-hop (depth 5)
        hop4_reachable = bfs_with_depth_limit(graph, icao, max_depth=5)
        for target in hop4_reachable:
            if target not in direct_neighbors and target not in hop1_reachable and target not in hop2_reachable and target not in hop3_reachable:
                pair = tuple(sorted([icao, target]))
                hop4_pairs.add(pair)
        
        # 5-hop (depth 6)
        hop5_reachable = bfs_with_depth_limit(graph, icao, max_depth=6)
        for target in hop5_reachable:
            if target not in direct_neighbors and target not in hop1_reachable and target not in hop2_reachable and target not in hop3_reachable and target not in hop4_reachable:
                pair = tuple(sorted([icao, target]))
                hop5_pairs.add(pair)
    
    # Calculate cumulative pairs (each level includes previous levels)
    cumulative_direct = len(direct_pairs)
    cumulative_1hop = cumulative_direct + len(hop1_pairs)
    cumulative_2hop = cumulative_1hop + len(hop2_pairs)
    cumulative_3hop = cumulative_2hop + len(hop3_pairs)
    cumulative_4hop = cumulative_3hop + len(hop4_pairs)
    cumulative_5hop = cumulative_4hop + len(hop5_pairs)
    
    hop_data = {
        'direct': cumulative_direct,
        '1hop': cumulative_1hop,
        '2hop': cumulative_2hop,
        '3hop': cumulative_3hop,
        '4hop': cumulative_4hop,
        '5hop': cumulative_5hop
    }
    
    # Calculate marginal improvement (additional pairs gained per hop)
    marginal_improvement = {
        '1hop': len(hop1_pairs),
        '2hop': len(hop2_pairs),
        '3hop': len(hop3_pairs),
        '4hop': len(hop4_pairs),
        '5hop': len(hop5_pairs)
    }
    
    # Find the "knee" - where marginal improvement drops significantly
    # Knee is typically where marginal improvement drops below 30% of max
    knee_hop = None
    max_marginal = max(marginal_improvement.values()) if marginal_improvement.values() else 0
    threshold = max_marginal * 0.3  # Knee is where improvement drops to 30% of max
    
    for hop in ['1hop', '2hop', '3hop', '4hop', '5hop']:
        if marginal_improvement[hop] < threshold and knee_hop is None and max_marginal > 0:
            knee_hop = hop
            break
    
    return {
        'cumulative_pairs': hop_data,
        'marginal_improvement': marginal_improvement,
        'knee_hop': knee_hop,
        'total_aircraft': len(aircraft_list),
        'max_possible_pairs': len(aircraft_list) * (len(aircraft_list) - 1) // 2 if len(aircraft_list) > 1 else 0
    }


def calculate_all_los_metrics(aircraft_list: List[Dict],
                             distances: List[Dict],
                             carrier_ranges: Dict[str, float]) -> Dict:
    """
    Calculate all LOS metrics (coverage, connectivity, geographic).
    
    Args:
        aircraft_list: List of aircraft dictionaries
        distances: List of distance calculations
        carrier_ranges: Dictionary mapping carrier codes to communication range (km)
    
    Returns:
        Dictionary with all metrics organized by category
    """
    coverage = calculate_los_coverage_metrics(distances)
    connectivity = calculate_los_connectivity_metrics(aircraft_list, distances, carrier_ranges)
    geographic = calculate_los_geographic_metrics(aircraft_list, distances)
    
    return {
        'coverage': coverage,
        'connectivity': connectivity,
        'geographic': geographic,
    }

