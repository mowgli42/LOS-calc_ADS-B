# ADS-B Line of Sight Calculator

## ADDED Requirements

### Requirement: Aircraft Data Ingestion
The system SHALL ingest real-time aircraft ADS-B data from the OpenSky Network API.

#### Scenario: Successful data fetch
- **WHEN** the system requests aircraft data from OpenSky Network API
- **THEN** the system receives and parses state vectors containing position (latitude, longitude, altitude), velocity, callsign, and ICAO24 identifier
- **AND** the system handles API errors gracefully with appropriate logging

#### Scenario: API rate limiting
- **WHEN** the API rate limit is exceeded
- **THEN** the system returns cached data if available
- **AND** the system logs the rate limit event

### Requirement: Carrier Filtering
The system SHALL filter aircraft by carrier using ICAO airline designator codes for the top 25 worldwide carriers.

#### Scenario: Filter by single carrier
- **WHEN** a user selects a carrier from the filter (e.g., Delta airlines)
- **THEN** the system displays only aircraft with callsigns matching that carrier's ICAO designator (e.g., DAL for Delta Air Lines)
- **AND** distance calculations include only selected carrier aircraft
- **AND** the system uses that carrier's specific communication range threshold

#### Scenario: Filter by multiple carriers
- **WHEN** a user selects multiple carriers from the top 25 worldwide carriers
- **THEN** the system displays aircraft matching any of the selected carriers' ICAO designators
- **AND** distance calculations consider all pairs within the selected carrier set
- **AND** the system uses carrier-specific communication ranges when determining connectivity

### Requirement: Line of Sight Distance Calculation
The system SHALL calculate the shortest line-of-sight distance between aircraft pairs using radio horizon calculations.

#### Scenario: Calculate distance between two aircraft
- **WHEN** two aircraft positions and altitudes are provided
- **THEN** the system calculates the 3D Euclidean distance between them
- **AND** the system calculates the radio horizon distance using formula: `d = sqrt(2 * R * h1) + sqrt(2 * R * h2)` where R is Earth radius (6,371 km) and h1, h2 are altitudes in km
- **AND** if 3D distance ≤ radio horizon distance, the aircraft are considered within line of sight

#### Scenario: Find shortest LOS distance for all pairs
- **WHEN** aircraft data for selected carriers is available
- **THEN** the system calculates line-of-sight distances for all aircraft pairs
- **AND** the system returns the shortest distance for each unique pair

### Requirement: Distance Visualization
The system SHALL display calculated distances in a bar graph grouped by distance bins.

#### Scenario: Render distance bar graph
- **WHEN** distance calculations are complete
- **THEN** the system groups distances into bins: 0-50km, 50-100km, 100-150km, 150-200km, 200km+
- **AND** the system displays a bar graph with count of aircraft pairs in each bin
- **AND** the graph updates when new data is loaded or carriers are reselected

### Requirement: Communication Path Analysis
The system SHALL analyze and count aircraft able to communicate directly versus through multi-hop paths.

#### Scenario: Direct communication count
- **WHEN** aircraft distances are calculated and carrier-specific communication range thresholds are configured
- **THEN** the system builds a connectivity graph where edges represent aircraft within communication range
- **AND** the system uses each aircraft's carrier-specific communication range threshold to determine connectivity
- **AND** the system counts the number of unique aircraft pairs that can communicate directly (distance ≤ carrier-specific threshold)

#### Scenario: Single-hop communication count
- **WHEN** the connectivity graph is built
- **THEN** the system uses breadth-first search (BFS) to find aircraft reachable through exactly one intermediate aircraft
- **AND** the system counts unique aircraft pairs reachable in 2 hops (1 intermediate)

#### Scenario: Two-hop communication count
- **WHEN** the connectivity graph is built
- **THEN** the system uses BFS to find aircraft reachable through exactly two intermediate aircraft
- **AND** the system counts unique aircraft pairs reachable in 3 hops (2 intermediates)

#### Scenario: Three-hop communication count
- **WHEN** the connectivity graph is built
- **THEN** the system uses BFS to find aircraft reachable through exactly three intermediate aircraft
- **AND** the system counts unique aircraft pairs reachable in 4 hops (3 intermediates)

### Requirement: Communication Statistics Display
The system SHALL display counts for direct, 1-hop, 2-hop, and 3-hop communication paths.

#### Scenario: Display communication statistics
- **WHEN** communication path analysis is complete
- **THEN** the system displays separate counts for:
  - Direct connections
  - 1-hop connections
  - 2-hop connections
  - 3-hop connections
- **AND** the statistics update when new data is loaded or carriers are reselected

### Requirement: Automatic Data Refresh
The system SHALL automatically refresh aircraft data every 15 minutes.

#### Scenario: Periodic data refresh
- **WHEN** 15 minutes (900 seconds) have elapsed since the last data fetch
- **THEN** the system automatically fetches new aircraft data from OpenSky API
- **AND** the system recalculates distances and communication paths
- **AND** the system updates all displays with new data
- **AND** the update status indicator shows the refresh timestamp

#### Scenario: Manual refresh trigger
- **WHEN** a user triggers a manual refresh
- **THEN** the system immediately fetches new data and updates displays
- **AND** the automatic refresh timer resets

### Requirement: Carrier-Specific Communication Range Configuration
The system SHALL support carrier-specific communication range thresholds for each of the top 25 worldwide carriers.

#### Scenario: Set carrier-specific communication range
- **WHEN** a user configures a communication range for a specific carrier (e.g., 200 km for Delta)
- **THEN** the system stores that carrier's communication range threshold
- **AND** the system uses that carrier-specific threshold to determine which aircraft pairs can communicate directly
- **AND** the system recalculates communication path statistics using carrier-specific thresholds
- **AND** the graph analysis updates accordingly
- **AND** different carriers can have different communication range values

#### Scenario: Default communication ranges
- **WHEN** a carrier does not have a configured communication range
- **THEN** the system uses a default communication range threshold (e.g., 200 km)
- **AND** the system allows users to override the default per carrier

### Requirement: Minimalistic Web Interface
The system SHALL provide a minimalistic web interface with dark theme, green tints, and small icons.

#### Scenario: Load web interface
- **WHEN** a user navigates to the application URL
- **THEN** the system displays a minimalistic interface with:
  - Dark background theme with green accent colors
  - Small icons for visual elements (carrier selection, statistics, refresh)
  - Carrier selection checkboxes for top 25 worldwide carriers
  - Distance bar graph area with dark theme styling
  - Communication statistics panel with green-tinted highlights
  - Configuration panel with carrier-specific communication range inputs
  - Update status indicator showing last refresh time

#### Scenario: Minimalistic design elements
- **WHEN** the web interface is displayed
- **THEN** all visual elements use a dark color scheme (dark background, light text)
- **AND** accent colors use green tints for highlights and important data
- **AND** icons are small and unobtrusive, maintaining minimalistic aesthetic
- **AND** the layout is clean and uncluttered, emphasizing data over decoration

#### Scenario: Select carriers and update display
- **WHEN** a user selects or deselects carrier checkboxes from the top 25 carriers
- **THEN** the system filters aircraft data to selected carriers
- **AND** the system uses carrier-specific communication range thresholds
- **AND** the system recalculates distances and communication paths
- **AND** the system updates the bar graph and statistics display with green-tinted highlights

