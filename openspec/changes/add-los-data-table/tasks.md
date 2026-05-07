## 1. Backend API

- [ ] 1.1 Add `POST /api/los-table` endpoint in `app.py` that accepts `{carriers, carrier_ranges?, include_airports?}`, calls `calculate_all_pair_distances()` and optionally `calculate_airport_to_aircraft_distances()`, and returns the full un-truncated pair list with all fields (icao24, callsign, carrier_code, distance_km, radio_horizon_km, los_distance_km, within_los, geo_altitude for both aircraft)
- [ ] 1.2 Include altitude data (geo_altitude in meters) for both aircraft in each pair record so the table can display altitude columns

## 2. Frontend Table Rendering

- [ ] 2.1 Add a "LOS Data Table" collapsible panel section in `templates/index.html` below the LOS Metrics section, following the existing panel pattern (dark theme, green accents)
- [ ] 2.2 Implement `fetchLosTableData()` in `static/js/main.js` to call `/api/los-table` with the currently selected carriers, carrier ranges, and airport toggle state
- [ ] 2.3 Implement `renderLosTable(data)` in `static/js/main.js` to dynamically build an HTML `<table>` with columns: Aircraft 1, Aircraft 2, Carrier 1, Carrier 2, Distance (km), Radio Horizon (km), LOS Distance (km), LOS Status, Alt 1 (m), Alt 2 (m)
- [ ] 2.4 Add client-side pagination: display the first 100 rows by default with a page-size selector (50/100/250/All)

## 3. Sorting

- [ ] 3.1 Add click handlers to column headers that sort the in-memory data array and re-render the table
- [ ] 3.2 Support ascending/descending toggle on repeated clicks with a sort direction indicator arrow on the active header
- [ ] 3.3 Handle both numeric sorting (distance, altitude) and alphabetical sorting (callsign, carrier)

## 4. Filtering

- [ ] 4.1 Add a filter bar above the table with: a text input for carrier code filter, a dropdown for LOS status (All / Within LOS / Outside LOS), and min/max distance number inputs
- [ ] 4.2 Implement client-side filter logic that applies all active filters as an AND condition before rendering
- [ ] 4.3 Update the displayed row count label to reflect the filtered/total pair count

## 5. Styling and Integration

- [ ] 5.1 Add CSS styles in `static/css/style.css` for the data table: dark background, green header accents, alternating row shading, hover highlight, sort indicator arrows, and responsive layout
- [ ] 5.2 Wire the table data fetch into the existing carrier selection change handler so the table updates whenever carriers are reselected or data refreshes
- [ ] 5.3 Handle the empty state: show a "Select carriers to view LOS pair data" message when no carriers are selected
