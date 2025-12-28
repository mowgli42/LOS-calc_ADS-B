"""
Multi-hop communication path analysis using graph traversal.
"""

from typing import Dict, List, Set, Tuple
from collections import deque, defaultdict
from config import CARRIERS, DEFAULT_COMMUNICATION_RANGE_KM


def build_connectivity_graph(aircraft_list: List[Dict], 
                            distances: List[Dict],
                            carrier_ranges: Dict[str, float]) -> Dict[str, Set[str]]:
    """
    Build connectivity graph where edges represent aircraft within communication range.
    
    Args:
        aircraft_list: List of aircraft dictionaries with icao24
        distances: List of distance calculations between aircraft pairs
        carrier_ranges: Dictionary mapping carrier codes to communication range (km)
    
    Returns:
        Adjacency list representation: {icao24: set of connected icao24s}
    """
    # Create mapping from icao24 to carrier for quick lookup
    aircraft_by_icao = {a['icao24']: a for a in aircraft_list}
    
    # Build graph
    graph = defaultdict(set)
    
    for dist_info in distances:
        icao1 = dist_info['aircraft1']['icao24']
        icao2 = dist_info['aircraft2']['icao24']
        distance = dist_info['distance_km']
        
        # Get carrier-specific communication ranges
        carrier1 = aircraft_by_icao.get(icao1, {}).get('carrier_code')
        carrier2 = aircraft_by_icao.get(icao2, {}).get('carrier_code')
        
        range1 = carrier_ranges.get(carrier1, DEFAULT_COMMUNICATION_RANGE_KM) if carrier1 else DEFAULT_COMMUNICATION_RANGE_KM
        range2 = carrier_ranges.get(carrier2, DEFAULT_COMMUNICATION_RANGE_KM) if carrier2 else DEFAULT_COMMUNICATION_RANGE_KM
        
        # Use the more restrictive range (both aircraft must be within range of each other)
        max_range = min(range1, range2)
        
        # Add edge if within carrier-specific communication range (no LOS requirement)
        if distance <= max_range:
            graph[icao1].add(icao2)
            graph[icao2].add(icao1)
    
    return dict(graph)


def bfs_with_depth_limit(graph: Dict[str, Set[str]], 
                        start: str, 
                        max_depth: int) -> Set[str]:
    """
    Breadth-first search with depth limit to find reachable nodes.
    
    Args:
        graph: Adjacency list representation
        start: Starting node (aircraft ICAO24)
        max_depth: Maximum number of hops (depth)
    
    Returns:
        Set of reachable aircraft ICAO24s within max_depth hops
    """
    if start not in graph:
        return set()
    
    visited = set()
    queue = deque([(start, 0)])  # (node, depth)
    visited.add(start)
    reachable = set()
    
    while queue:
        node, depth = queue.popleft()
        
        if depth > 0:  # Don't count the starting node itself
            reachable.add(node)
        
        if depth < max_depth:
            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
    
    return reachable


def get_graph_data(aircraft_list: List[Dict],
                   distances: List[Dict],
                   carrier_ranges: Dict[str, float]) -> Dict:
    """
    Get graph data structure with nodes (aircraft) and edges (connections) with distances.
    
    Args:
        aircraft_list: List of aircraft dictionaries
        distances: List of distance calculations
        carrier_ranges: Dictionary mapping carrier codes to communication range (km)
    
    Returns:
        Dictionary with 'nodes' and 'edges' lists
    """
    graph = build_connectivity_graph(aircraft_list, distances, carrier_ranges)
    
    # Create nodes from aircraft list
    nodes = []
    aircraft_by_icao = {a['icao24']: a for a in aircraft_list}
    for aircraft in aircraft_list:
        nodes.append({
            'id': aircraft['icao24'],
            'label': aircraft.get('callsign') or aircraft['icao24'],
            'carrier': aircraft.get('carrier_code', ''),
            'latitude': aircraft.get('latitude'),
            'longitude': aircraft.get('longitude'),
        })
    
    # Create edges with distance information
    edges = []
    edge_set = set()  # To avoid duplicates
    
    for dist_info in distances:
        icao1 = dist_info['aircraft1']['icao24']
        icao2 = dist_info['aircraft2']['icao24']
        distance = dist_info['distance_km']
        
        # Check if this edge should exist in the connectivity graph
        if icao1 in graph and icao2 in graph[icao1]:
            # Create unique edge identifier
            edge_id = tuple(sorted([icao1, icao2]))
            if edge_id not in edge_set:
                edge_set.add(edge_id)
                edges.append({
                    'from': icao1,
                    'to': icao2,
                    'distance': distance,
                })
    
    return {
        'nodes': nodes,
        'edges': edges,
    }


def count_communication_paths(aircraft_list: List[Dict],
                             distances: List[Dict],
                             carrier_ranges: Dict[str, float]) -> Dict[str, int]:
    """
    Count aircraft pairs able to communicate via direct, 1-hop, 2-hop, and 3-hop paths.
    
    Args:
        aircraft_list: List of aircraft dictionaries
        distances: List of distance calculations
        carrier_ranges: Dictionary mapping carrier codes to communication range (km)
    
    Returns:
        Dictionary with counts: {'direct': N, '1hop': N, '2hop': N, '3hop': N}
    """
    graph = build_connectivity_graph(aircraft_list, distances, carrier_ranges)
    
    all_aircraft = {a['icao24'] for a in aircraft_list}
    
    direct_pairs = set()
    hop1_pairs = set()
    hop2_pairs = set()
    hop3_pairs = set()
    
    for aircraft in aircraft_list:
        icao = aircraft['icao24']
        
        # Direct connections (immediate neighbors)
        direct_neighbors = graph.get(icao, set())
        for neighbor in direct_neighbors:
            pair = tuple(sorted([icao, neighbor]))
            direct_pairs.add(pair)
        
        # 1-hop (depth 2: start -> intermediate -> target)
        hop1_reachable = bfs_with_depth_limit(graph, icao, max_depth=2)
        for target in hop1_reachable:
            if target not in direct_neighbors:  # Not already direct
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
    
    return {
        'direct': len(direct_pairs),
        '1hop': len(hop1_pairs),
        '2hop': len(hop2_pairs),
        '3hop': len(hop3_pairs),
    }

