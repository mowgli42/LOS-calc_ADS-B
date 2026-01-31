# Change: Add ADS-B Line of Sight Calculator

## Why
Enable real-time analysis of aircraft line-of-sight distances and communication path analysis from ADS-B data. This provides visibility into aircraft proximity and communication connectivity for selected commercial carriers, supporting operational decision-making and network analysis.

## What Changes
- Add simple Flask web application backend with REST API endpoints for aircraft data, distance calculations, and communication analysis
- Add OpenSky Network API integration for real-time ADS-B data ingestion
- Add radio horizon line-of-sight distance calculation engine
- Add multi-hop communication path analysis (direct, 1-hop, 2-hop, 3-hop)
- Add minimalistic web interface with dark theme, green tints, and small icons
- Add carrier selection, distance bar graphs, and communication statistics display
- Add automatic data refresh every 15 minutes
- Add carrier filtering by ICAO airline designator codes for top 25 worldwide carriers
- Add carrier-specific communication range configuration

## Impact
- Affected specs: New capability `adsb-los-calculator`
- Affected code: New files across backend (Python Flask) and frontend (HTML/CSS/JS) - simple, minimalistic implementation
- External dependencies: OpenSky Network API (public, rate-limited)
- Configuration: Carrier-specific communication range thresholds, 15-minute refresh interval, top 25 carrier mappings

