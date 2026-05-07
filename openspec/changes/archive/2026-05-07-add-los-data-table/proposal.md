## Why

The application currently displays LOS calculation results only through aggregate visualizations (charts, maps, metric panels). There is no way to inspect individual aircraft pair data — users cannot see, sort, or filter the raw LOS pair records that drive the aggregate statistics. A sortable, filterable data table would let analysts drill into specific pairs, identify outliers, and export subsets for further analysis.

## What Changes

- Add a new API endpoint `POST /api/los-table` that returns paginated, sortable, filterable LOS pair data for selected carriers
- Add a new frontend data table panel in the web UI below the existing LOS Metrics section
- The table displays per-pair columns: Aircraft 1 callsign/ICAO24, Aircraft 2 callsign/ICAO24, carrier codes, 3D distance (km), radio horizon (km), LOS distance (km), within-LOS status, and altitude data
- Support client-side column sorting (ascending/descending) on all numeric and text columns
- Support client-side filtering by carrier, LOS status, and distance range
- Include airport-to-aircraft pairs when the "Include Airports" toggle is enabled
- Match the existing dark theme with green accents

## Capabilities

### New Capabilities
- `los-data-table`: Sortable, filterable tabular view of individual LOS pair calculations

### Modified Capabilities
- `adsb-los-calculator`: Add the LOS Data Table requirement to the existing ADS-B LOS Calculator capability

## Impact

- Affected code: `app.py` (new `/api/los-table` endpoint), `templates/index.html` (new table panel HTML), `static/js/main.js` (table rendering, sorting, filtering logic), `static/css/style.css` (table styling)
- Affected specs: `adsb-los-calculator`
- No new dependencies — the table is built with vanilla HTML/CSS/JS to match the existing stack
