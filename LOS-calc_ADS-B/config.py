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

# Military aircraft groups with ICAO24 address ranges and origin countries
# Address ranges are in hex format (24-bit addresses)
MILITARY_GROUPS = {
    'US_MIL': {
        'name': 'US Military',
        'default_range_km': 200,
        'address_ranges': [
            ('AE0000', 'AFFFFF'),  # US Military
        ],
        'origin_countries': ['United States']
    },
    'UK_MIL': {
        'name': 'UK Military',
        'default_range_km': 200,
        'address_ranges': [
            ('400000', '43FFFF'),  # UK Military
        ],
        'origin_countries': ['United Kingdom']
    },
    'FR_MIL': {
        'name': 'France Military',
        'default_range_km': 200,
        'address_ranges': [
            ('380000', '3BFFFF'),  # France Military
        ],
        'origin_countries': ['France']
    },
    'DE_MIL': {
        'name': 'Germany Military',
        'default_range_km': 200,
        'address_ranges': [
            ('3C0000', '3FFFFF'),  # Germany Military
        ],
        'origin_countries': ['Germany']
    },
    'IT_MIL': {
        'name': 'Italy Military',
        'default_range_km': 200,
        'address_ranges': [
            ('33D000', '33FFFF'),  # Italy Military
        ],
        'origin_countries': ['Italy']
    },
    'CA_MIL': {
        'name': 'Canada Military',
        'default_range_km': 200,
        'address_ranges': [
            ('C00000', 'C3FFFF'),  # Canada Military
        ],
        'origin_countries': ['Canada']
    },
    'RU_MIL': {
        'name': 'Russia Military',
        'default_range_km': 200,
        'address_ranges': [
            ('150000', '15FFFF'),  # Russia Military
            ('680000', '6BFFFF'),  # Russia Military (additional range)
        ],
        'origin_countries': ['Russia']
    },
    'CN_MIL': {
        'name': 'China Military',
        'default_range_km': 200,
        'address_ranges': [
            ('780000', '7BFFFF'),  # China Military
        ],
        'origin_countries': ['China']
    },
    'IN_MIL': {
        'name': 'India Military',
        'default_range_km': 200,
        'address_ranges': [
            ('800000', '83FFFF'),  # India Military
        ],
        'origin_countries': ['India']
    },
    'JP_MIL': {
        'name': 'Japan Military',
        'default_range_km': 200,
        'address_ranges': [
            ('840000', '87FFFF'),  # Japan Military
        ],
        'origin_countries': ['Japan']
    },
    'AU_MIL': {
        'name': 'Australia Military',
        'default_range_km': 200,
        'address_ranges': [
            ('7C0000', '7FFFFF'),  # Australia Military
        ],
        'origin_countries': ['Australia']
    },
}

# Default communication range if carrier not found
DEFAULT_COMMUNICATION_RANGE_KM = 200

# Data refresh interval in seconds (15 minutes)
REFRESH_INTERVAL_SECONDS = 900

# OpenSky Network API endpoint
OPENSKY_API_URL = 'https://opensky-network.org/api/states/all'

# Earth radius in kilometers (for radio horizon calculations)
EARTH_RADIUS_KM = 6371

# Maximum practical line-of-sight range (160 nautical miles)
# This represents the practical limit for air-to-air communication systems
MAX_LOS_RANGE_KM = 160 * 1.852  # 160 nautical miles in km ≈ 296.32 km

# Distance bins for visualization (in km)
DISTANCE_BINS = [
    (0, 50),
    (50, 100),
    (100, 150),
    (150, 200),
    (200, float('inf'))
]

# Top 50 airports by aircraft traffic (ICAO codes, coordinates, elevation)
TOP_50_AIRPORTS = {
    'KATL': {'name': 'Hartsfield-Jackson Atlanta International', 'latitude': 33.6367, 'longitude': -84.4281, 'elevation_m': 313},
    'KDFW': {'name': 'Dallas/Fort Worth International', 'latitude': 32.8969, 'longitude': -97.0381, 'elevation_m': 185},
    'KDEN': {'name': 'Denver International', 'latitude': 39.8617, 'longitude': -104.6731, 'elevation_m': 1655},
    'KORD': {'name': "Chicago O'Hare International", 'latitude': 41.9786, 'longitude': -87.9048, 'elevation_m': 203},
    'KLAX': {'name': 'Los Angeles International', 'latitude': 33.9425, 'longitude': -118.4081, 'elevation_m': 38},
    'KJFK': {'name': 'John F. Kennedy International', 'latitude': 40.6398, 'longitude': -73.7789, 'elevation_m': 4},
    'KCLT': {'name': 'Charlotte Douglas International', 'latitude': 35.2144, 'longitude': -80.9473, 'elevation_m': 228},
    'KMIA': {'name': 'Miami International', 'latitude': 25.7933, 'longitude': -80.2906, 'elevation_m': 2},
    'KSEA': {'name': 'Seattle-Tacoma International', 'latitude': 47.4500, 'longitude': -122.3089, 'elevation_m': 132},
    'KLAS': {'name': 'McCarran International', 'latitude': 36.0840, 'longitude': -115.1537, 'elevation_m': 665},
    'KPHX': {'name': 'Phoenix Sky Harbor International', 'latitude': 33.4343, 'longitude': -112.0116, 'elevation_m': 346},
    'KIAH': {'name': 'George Bush Intercontinental', 'latitude': 29.9844, 'longitude': -95.3414, 'elevation_m': 30},
    'KEWR': {'name': 'Newark Liberty International', 'latitude': 40.6925, 'longitude': -74.1687, 'elevation_m': 5},
    'KMSP': {'name': 'Minneapolis-Saint Paul International', 'latitude': 44.8820, 'longitude': -93.2218, 'elevation_m': 256},
    'KDTW': {'name': 'Detroit Metropolitan', 'latitude': 42.2162, 'longitude': -83.3554, 'elevation_m': 197},
    'KBOS': {'name': 'Logan International', 'latitude': 42.3656, 'longitude': -71.0096, 'elevation_m': 6},
    'KSFO': {'name': 'San Francisco International', 'latitude': 37.6213, 'longitude': -122.3790, 'elevation_m': 4},
    'KPHL': {'name': 'Philadelphia International', 'latitude': 39.8719, 'longitude': -75.2411, 'elevation_m': 11},
    'KLGA': {'name': 'LaGuardia', 'latitude': 40.7769, 'longitude': -73.8740, 'elevation_m': 7},
    'KBWI': {'name': 'Baltimore/Washington International', 'latitude': 39.1774, 'longitude': -76.6684, 'elevation_m': 45},
    'KDCA': {'name': 'Ronald Reagan Washington National', 'latitude': 38.8521, 'longitude': -77.0377, 'elevation_m': 5},
    'KMCO': {'name': 'Orlando International', 'latitude': 28.4294, 'longitude': -81.3090, 'elevation_m': 29},
    'KSLC': {'name': 'Salt Lake City International', 'latitude': 40.7899, 'longitude': -111.9791, 'elevation_m': 1288},
    'KMDW': {'name': 'Chicago Midway International', 'latitude': 41.7868, 'longitude': -87.7522, 'elevation_m': 189},
    'KSTL': {'name': 'St. Louis Lambert International', 'latitude': 38.7487, 'longitude': -90.3700, 'elevation_m': 188},
    'KPDX': {'name': 'Portland International', 'latitude': 45.5898, 'longitude': -122.5951, 'elevation_m': 9},
    'KSAN': {'name': 'San Diego International', 'latitude': 32.7338, 'longitude': -117.1933, 'elevation_m': 5},
    'KHOU': {'name': 'William P. Hobby', 'latitude': 29.6454, 'longitude': -95.2789, 'elevation_m': 14},
    'KDAL': {'name': 'Dallas Love Field', 'latitude': 32.8471, 'longitude': -96.8518, 'elevation_m': 148},
    'KAUS': {'name': 'Austin-Bergstrom International', 'latitude': 30.1945, 'longitude': -97.6699, 'elevation_m': 165},
    'KTPA': {'name': 'Tampa International', 'latitude': 27.9755, 'longitude': -82.5332, 'elevation_m': 8},
    'KMCI': {'name': 'Kansas City International', 'latitude': 39.2976, 'longitude': -94.7139, 'elevation_m': 312},
    'KIND': {'name': 'Indianapolis International', 'latitude': 39.7173, 'longitude': -86.2944, 'elevation_m': 243},
    'KBNA': {'name': 'Nashville International', 'latitude': 36.1245, 'longitude': -86.6782, 'elevation_m': 183},
    'KRDU': {'name': 'Raleigh-Durham International', 'latitude': 35.8776, 'longitude': -78.7875, 'elevation_m': 132},
    'KMSY': {'name': 'Louis Armstrong New Orleans International', 'latitude': 29.9934, 'longitude': -90.2581, 'elevation_m': 1},
    'KCVG': {'name': 'Cincinnati/Northern Kentucky International', 'latitude': 39.0488, 'longitude': -84.6678, 'elevation_m': 273},
    'KCMH': {'name': 'John Glenn Columbus International', 'latitude': 39.9980, 'longitude': -82.8919, 'elevation_m': 248},
    'KSAV': {'name': 'Savannah/Hilton Head International', 'latitude': 32.1276, 'longitude': -81.2021, 'elevation_m': 15},
    'KJAX': {'name': 'Jacksonville International', 'latitude': 30.4941, 'longitude': -81.6879, 'elevation_m': 9},
    'KRSW': {'name': 'Southwest Florida International', 'latitude': 26.5362, 'longitude': -81.7552, 'elevation_m': 9},
    'KPBI': {'name': 'Palm Beach International', 'latitude': 26.6832, 'longitude': -80.0956, 'elevation_m': 6},
    'KSMF': {'name': 'Sacramento International', 'latitude': 38.6954, 'longitude': -121.5908, 'elevation_m': 8},
    'KOAK': {'name': 'Oakland International', 'latitude': 37.7213, 'longitude': -122.2207, 'elevation_m': 3},
    'KSJC': {'name': 'Norman Y. Mineta San Jose International', 'latitude': 37.3626, 'longitude': -121.9290, 'elevation_m': 19},
    'KONT': {'name': 'Ontario International', 'latitude': 34.0560, 'longitude': -117.6012, 'elevation_m': 288},
    'KBUR': {'name': 'Bob Hope', 'latitude': 34.2006, 'longitude': -118.3587, 'elevation_m': 236},
    'KOGG': {'name': 'Kahului', 'latitude': 20.8986, 'longitude': -156.4306, 'elevation_m': 15},
    'PHNL': {'name': 'Daniel K. Inouye International', 'latitude': 21.3206, 'longitude': -157.9242, 'elevation_m': 4},
    'PANC': {'name': 'Ted Stevens Anchorage International', 'latitude': 61.1744, 'longitude': -149.9961, 'elevation_m': 46},
}
