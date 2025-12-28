"""
Radio horizon line-of-sight distance calculations between aircraft.
"""

import math
from typing import Dict, List, Tuple
from config import EARTH_RADIUS_KM

def calculate_3d_distance(aircraft1: Dict, aircraft2: Dict) -> float:
    """
    Calculate 3D Euclidean distance between two aircraft.
    Uses great circle distance for lat/lon and includes altitude difference.
    
    Args:
        aircraft1: First aircraft with latitude, longitude, geo_altitude (meters)
        aircraft2: Second aircraft with latitude, longitude, geo_altitude (meters)
    
    Returns:
        Distance in kilometers
    """
    lat1 = math.radians(aircraft1['latitude'])
    lon1 = math.radians(aircraft1['longitude'])
    lat2 = math.radians(aircraft2['latitude'])
    lon2 = math.radians(aircraft2['longitude'])
    
    # Great circle distance (Haversine formula)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Surface distance in km
    surface_distance_km = EARTH_RADIUS_KM * c
    
    # Altitude difference in km
    alt1_km = (aircraft1.get('geo_altitude', 0) or 0) / 1000.0
    alt2_km = (aircraft2.get('geo_altitude', 0) or 0) / 1000.0
    alt_diff_km = abs(alt1_km - alt2_km)
    
    # 3D Euclidean distance
    distance_3d = math.sqrt(surface_distance_km**2 + alt_diff_km**2)
    
    return distance_3d


def calculate_radio_horizon(aircraft1: Dict, aircraft2: Dict) -> float:
    """
    Calculate radio horizon distance between two aircraft.
    
    Formula: d = sqrt(2 * R * h1) + sqrt(2 * R * h2)
    where R is Earth radius and h1, h2 are aircraft altitudes in km.
    
    Args:
        aircraft1: First aircraft with geo_altitude (meters)
        aircraft2: Second aircraft with geo_altitude (meters)
    
    Returns:
        Radio horizon distance in kilometers
    """
    # Convert altitude from meters to kilometers
    h1_km = (aircraft1.get('geo_altitude', 0) or 0) / 1000.0
    h2_km = (aircraft2.get('geo_altitude', 0) or 0) / 1000.0
    
    # Ensure non-negative altitudes
    h1_km = max(0, h1_km)
    h2_km = max(0, h2_km)
    
    # Radio horizon formula
    horizon1 = math.sqrt(2 * EARTH_RADIUS_KM * h1_km)
    horizon2 = math.sqrt(2 * EARTH_RADIUS_KM * h2_km)
    
    return horizon1 + horizon2


def is_within_line_of_sight(aircraft1: Dict, aircraft2: Dict) -> bool:
    """
    Check if two aircraft are within radio horizon line-of-sight.
    
    Args:
        aircraft1: First aircraft
        aircraft2: Second aircraft
    
    Returns:
        True if 3D distance <= radio horizon distance
    """
    distance_3d = calculate_3d_distance(aircraft1, aircraft2)
    radio_horizon = calculate_radio_horizon(aircraft1, aircraft2)
    
    return distance_3d <= radio_horizon


def calculate_all_pair_distances(aircraft_list: List[Dict]) -> List[Dict]:
    """
    Calculate line-of-sight distances for all aircraft pairs.
    Returns all pairs with their distances, marking which are within LOS.
    
    Args:
        aircraft_list: List of aircraft dictionaries
    
    Returns:
        List of dictionaries with aircraft pair info and distances
    """
    distances = []
    n = len(aircraft_list)
    
    for i in range(n):
        for j in range(i + 1, n):
            aircraft1 = aircraft_list[i]
            aircraft2 = aircraft_list[j]
            
            # Calculate distances
            distance_3d = calculate_3d_distance(aircraft1, aircraft2)
            radio_horizon = calculate_radio_horizon(aircraft1, aircraft2)
            within_los = distance_3d <= radio_horizon
            
            # For LOS pairs, use 3D distance as the LOS distance
            # For non-LOS pairs, still include distance for visualization
            los_distance = distance_3d if within_los else None
            
            distances.append({
                'aircraft1': {
                    'icao24': aircraft1['icao24'],
                    'callsign': aircraft1.get('callsign'),
                    'carrier': aircraft1.get('carrier_code'),
                },
                'aircraft2': {
                    'icao24': aircraft2['icao24'],
                    'callsign': aircraft2.get('callsign'),
                    'carrier': aircraft2.get('carrier_code'),
                },
                'distance_km': distance_3d,  # Always include 3D distance
                'los_distance_km': los_distance,  # LOS distance if within LOS
                'radio_horizon_km': radio_horizon,
                'within_los': within_los,
            })
    
    return distances

