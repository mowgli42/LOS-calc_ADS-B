"""
OpenSky Network API client for ingesting aircraft ADS-B data.
"""

import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime
from config import OPENSKY_API_URL, CARRIERS

logger = logging.getLogger(__name__)


class OpenSkyClient:
    """Client for fetching aircraft state data from OpenSky Network API."""
    
    def __init__(self):
        self.api_url = OPENSKY_API_URL
        self.last_fetch_time = None
        self.cached_data = None
    
    def fetch_aircraft_states(self) -> Optional[Dict]:
        """
        Fetch all aircraft states from OpenSky Network API.
        
        Returns:
            Dictionary with 'time' and 'states' keys, or None on error.
            States is a list of state vectors in OpenSky format.
        """
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            self.last_fetch_time = datetime.now()
            self.cached_data = data
            
            logger.info(f"Fetched {len(data.get('states', []))} aircraft states")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from OpenSky API: {e}")
            # Return cached data if available
            if self.cached_data:
                logger.info("Returning cached data due to API error")
                return self.cached_data
            return None
    
    def parse_state_vector(self, state_vector: List) -> Optional[Dict]:
        """
        Parse OpenSky state vector into structured format.
        
        OpenSky state vector format:
        [icao24, callsign, origin_country, time_position, last_contact,
         longitude, latitude, baro_altitude, on_ground, velocity, heading,
         vertical_rate, sensors, geo_altitude, squawk, spi, position_source]
        
        Returns:
            Dictionary with parsed aircraft data, or None if invalid.
        """
        if not state_vector or len(state_vector) < 11:
            return None
        
        try:
            # Extract key fields
            icao24 = state_vector[0]
            callsign = state_vector[1].strip() if state_vector[1] else None
            longitude = state_vector[5]
            latitude = state_vector[6]
            baro_altitude = state_vector[7]  # meters
            velocity = state_vector[9]  # m/s
            heading = state_vector[10]  # degrees
            geo_altitude = state_vector[13] if len(state_vector) > 13 and state_vector[13] else baro_altitude
            
            # Validate required fields
            if longitude is None or latitude is None:
                return None
            
            # Extract carrier code from callsign (typically first 3 characters)
            carrier_code = None
            if callsign and len(callsign) >= 3:
                carrier_code = callsign[:3].upper()
            
            return {
                'icao24': icao24,
                'callsign': callsign,
                'carrier_code': carrier_code,
                'longitude': longitude,
                'latitude': latitude,
                'baro_altitude': baro_altitude if baro_altitude else 0,
                'geo_altitude': geo_altitude if geo_altitude else (baro_altitude if baro_altitude else 0),
                'velocity': velocity if velocity else 0,
                'heading': heading if heading else 0,
            }
        except (ValueError, IndexError, AttributeError) as e:
            logger.warning(f"Error parsing state vector: {e}")
            return None
    
    def filter_by_carriers(self, states: List[List], carrier_codes: List[str]) -> List[Dict]:
        """
        Filter aircraft states by carrier ICAO codes.
        
        Args:
            states: List of OpenSky state vectors
            carrier_codes: List of ICAO carrier codes to include
            
        Returns:
            List of parsed aircraft dictionaries matching the carriers
        """
        if not states:
            return []
        
        filtered = []
        carrier_set = set(c.upper() for c in carrier_codes)
        
        for state_vector in states:
            aircraft = self.parse_state_vector(state_vector)
            if aircraft and aircraft.get('carrier_code') in carrier_set:
                filtered.append(aircraft)
        
        logger.info(f"Filtered to {len(filtered)} aircraft from {len(states)} total")
        return filtered
    
    def get_carrier_aircraft(self, carrier_codes: List[str]) -> List[Dict]:
        """
        Fetch and filter aircraft data for specified carriers.
        
        Args:
            carrier_codes: List of ICAO carrier codes
            
        Returns:
            List of aircraft dictionaries for the specified carriers
        """
        data = self.fetch_aircraft_states()
        if not data or 'states' not in data:
            return []
        
        return self.filter_by_carriers(data['states'], carrier_codes)

