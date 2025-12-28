"""
Configuration module for ADS-B LOS Calculator.
Defines carrier mappings, communication ranges, and system settings.
"""

# Top 25 worldwide carriers by ICAO designator codes
CARRIERS = {
    'AAL': {'name': 'American Airlines', 'default_range_km': 200},
    'DAL': {'name': 'Delta Air Lines', 'default_range_km': 200},
    'UAL': {'name': 'United Airlines', 'default_range_km': 200},
    'SWA': {'name': 'Southwest Airlines', 'default_range_km': 180},
    'DLH': {'name': 'Lufthansa', 'default_range_km': 220},
    'BAW': {'name': 'British Airways', 'default_range_km': 220},
    'AFR': {'name': 'Air France', 'default_range_km': 220},
    'UAE': {'name': 'Emirates', 'default_range_km': 240},
    'QTR': {'name': 'Qatar Airways', 'default_range_km': 240},
    'SIA': {'name': 'Singapore Airlines', 'default_range_km': 220},
    'JAL': {'name': 'Japan Airlines', 'default_range_km': 200},
    'KLM': {'name': 'KLM Royal Dutch Airlines', 'default_range_km': 220},
    'IBE': {'name': 'Iberia', 'default_range_km': 200},
    'ANA': {'name': 'All Nippon Airways', 'default_range_km': 200},
    'THA': {'name': 'Thai Airways', 'default_range_km': 200},
    'QFA': {'name': 'Qantas', 'default_range_km': 220},
    'TAM': {'name': 'LATAM', 'default_range_km': 200},
    'TUR': {'name': 'Turkish Airlines', 'default_range_km': 220},
    'ETD': {'name': 'Etihad Airways', 'default_range_km': 240},
    'CXA': {'name': 'Cathay Pacific', 'default_range_km': 220},
    'CSN': {'name': 'China Southern', 'default_range_km': 200},
    'CES': {'name': 'China Eastern', 'default_range_km': 200},
    'CAL': {'name': 'China Airlines', 'default_range_km': 200},
    'KAL': {'name': 'Korean Air', 'default_range_km': 200},
    'VIR': {'name': 'Virgin Atlantic', 'default_range_km': 220},
}

# Default communication range if carrier not found
DEFAULT_COMMUNICATION_RANGE_KM = 200

# Data refresh interval in seconds (15 minutes)
REFRESH_INTERVAL_SECONDS = 900

# OpenSky Network API endpoint
OPENSKY_API_URL = 'https://opensky-network.org/api/states/all'

# Earth radius in kilometers (for radio horizon calculations)
EARTH_RADIUS_KM = 6371

# Distance bins for visualization (in km)
DISTANCE_BINS = [
    (0, 50),
    (50, 100),
    (100, 150),
    (150, 200),
    (200, float('inf'))
]

