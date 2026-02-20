## 1. Data Model
- [x] 1.1 Define Satellite schema (id, name, footprint_center_lat, footprint_center_lon, footprint_radius_km)
- [x] 1.2 Define Node planned usage (node_id, satellite_id, start_time, end_time)
- [x] 1.3 Implement in-memory or persistent storage
- [x] 1.4 Add API endpoints to CRUD satellites and node planned usage

## 2. Aggregation and Saturation
- [x] 2.1 Compute total nodes per satellite (for a given time or time range)
- [x] 2.2 Implement saturation detection: flag when node count in footprint exceeds threshold
- [x] 2.3 Add API endpoints for node counts per satellite and saturation status

## 3. Map Integration
- [x] 3.1 Add satellite footprint as selectable map layer (circle overlay)
- [x] 3.2 Render footprints with toggle; optionally color by saturation
- [x] 3.3 Show node count per satellite in layer or sidebar

## 4. UI
- [x] 4.1 Add UI to manage satellites (create, edit, list) and define footprints
- [x] 4.2 Add UI to add planned satellite usage to nodes (satellite, start/end time)
- [x] 4.3 Add UI to view nodes per satellite and saturation status
- [x] 4.4 Add map layer control for satellite footprints
