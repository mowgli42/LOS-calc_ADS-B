# ADS-B Line of Sight Calculator

## Purpose
Provide a web-based tool for calculating and visualizing line-of-sight distances between aircraft using ADS-B data, including multi-hop communication path analysis, carrier-specific range configuration, and tabular data inspection.

## Requirements

### Requirement: LOS Data Table API
The system SHALL provide a `POST /api/los-table` endpoint that returns the complete list of LOS pair calculations for selected carriers.

#### Scenario: Fetch LOS pair data for selected carriers
- **WHEN** a client sends a POST request to `/api/los-table` with a JSON body containing `carriers` (array of carrier codes), optional `carrier_ranges` (object mapping carrier codes to range in km), and optional `include_airports` (boolean)
- **THEN** the system returns a JSON response containing an array `pairs` where each entry includes: aircraft1 identifiers (icao24, callsign, carrier_code), aircraft2 identifiers (icao24, callsign, carrier_code), `distance_km` (3D Euclidean distance), `radio_horizon_km`, `los_distance_km` (distance if within LOS, else null), `within_los` (boolean), and altitude data for both aircraft (geo_altitude in meters)
- **AND** if `include_airports` is true, the response also includes airport-to-aircraft pairs with the airport identified by ICAO code and name

#### Scenario: No carriers selected
- **WHEN** a client sends a POST request to `/api/los-table` with an empty `carriers` array
- **THEN** the system returns a 400 error with message "No carriers selected"

#### Scenario: No aircraft data available
- **WHEN** a client sends a valid request but no aircraft match the selected carriers
- **THEN** the system returns a JSON response with an empty `pairs` array and `total_count` of 0

### Requirement: LOS Data Table UI Panel
The system SHALL display a sortable, filterable data table panel in the web interface showing individual LOS pair calculations.

#### Scenario: Render data table after carrier selection
- **WHEN** a user selects one or more carriers and LOS data is calculated
- **THEN** the system displays a table panel with columns: Aircraft 1 (callsign), Aircraft 2 (callsign), Carrier 1, Carrier 2, Distance (km), Radio Horizon (km), LOS Distance (km), LOS Status, Alt 1 (m), Alt 2 (m)
- **AND** the table is styled with the existing dark theme and green accents
- **AND** the table initially shows the first 100 rows with a control to adjust page size or show more

#### Scenario: Empty state
- **WHEN** no carriers are selected or no aircraft data is available
- **THEN** the table panel displays a message indicating no data is available (e.g., "Select carriers to view LOS pair data")

### Requirement: LOS Data Table Column Sorting
The system SHALL support sorting the LOS data table by clicking column headers.

#### Scenario: Sort by numeric column ascending
- **WHEN** a user clicks a column header for a numeric column (e.g., Distance)
- **THEN** the table rows are reordered in ascending order by that column's values
- **AND** a sort indicator (e.g., arrow) is displayed on the active column header

#### Scenario: Toggle sort direction
- **WHEN** a user clicks the same column header again
- **THEN** the sort direction toggles from ascending to descending (or vice versa)
- **AND** the sort indicator updates to reflect the new direction

#### Scenario: Sort by text column
- **WHEN** a user clicks a column header for a text column (e.g., Carrier 1)
- **THEN** the table rows are reordered alphabetically by that column's values

### Requirement: LOS Data Table Filtering
The system SHALL support filtering the LOS data table by carrier, LOS status, and distance range.

#### Scenario: Filter by carrier code
- **WHEN** a user enters a carrier code in the filter input
- **THEN** the table displays only rows where either Aircraft 1 or Aircraft 2 belongs to that carrier
- **AND** the row count updates to reflect the filtered set

#### Scenario: Filter by LOS status
- **WHEN** a user selects a LOS status filter (e.g., "Within LOS only" or "Outside LOS only")
- **THEN** the table displays only rows matching that LOS status

#### Scenario: Filter by distance range
- **WHEN** a user specifies a minimum and/or maximum distance value
- **THEN** the table displays only rows where the 3D distance falls within the specified range

#### Scenario: Combined filters
- **WHEN** a user applies multiple filters simultaneously (e.g., carrier "DAL" and LOS status "Within LOS")
- **THEN** the table displays only rows matching all active filter criteria
