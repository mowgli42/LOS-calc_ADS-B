# Satellite Communications Tracking

## ADDED Requirements

### Requirement: Satellite Footprint Definition
The system SHALL define satellites with a simple footprint (center and radius) for map visualization and saturation analysis.

#### Scenario: Define satellite with footprint
- **WHEN** a user creates or updates a satellite
- **THEN** the system stores: satellite id, name, footprint center (latitude, longitude), footprint radius (km)
- **AND** the footprint is represented as a circle on the map (no orbital mechanics)
- **AND** the system allows multiple satellites to be defined

#### Scenario: Footprint as selectable map layer
- **WHEN** a user enables the satellite footprint layer
- **THEN** the system displays each satellite's footprint as a circle overlay on the map
- **AND** the user can toggle the layer on or off
- **AND** the footprint geometry is computed simply (circle from center + radius)

### Requirement: Per-Node Planned Satellite Usage
The system SHALL capture when each node (e.g., aircraft) plans to use a satellite link.

#### Scenario: Add planned usage to node
- **WHEN** a user adds planned satellite usage for a node
- **THEN** the system stores: node id, satellite id, start time, end time (planned usage window)
- **AND** the system allows multiple planned usage windows per node (different satellites or time ranges)
- **AND** the data represents when the plane will be flying and using the satellite link

#### Scenario: Query nodes by satellite and time
- **WHEN** a user requests nodes for a satellite at a given time (or time range)
- **THEN** the system returns nodes whose planned usage window overlaps the query time
- **AND** the system returns total count of nodes per satellite for the query

### Requirement: Total Nodes Per Satellite
The system SHALL show the total number of nodes planned to use each satellite.

#### Scenario: Aggregate nodes per satellite
- **WHEN** a user requests node counts per satellite (optionally for a specific time)
- **THEN** the system returns for each satellite: satellite id, name, and count of nodes with overlapping planned usage
- **AND** the count reflects nodes that plan to use the satellite in the relevant time window

### Requirement: Satellite Footprint Saturation Identification
The system SHALL identify potential saturation when too many users plan to use the same satellite in overlapping time windows.

#### Scenario: Detect saturation
- **WHEN** the number of nodes with planned usage on a satellite (for a given time or time range) exceeds a configurable threshold
- **THEN** the system flags that satellite as potentially saturated
- **AND** the system supports a simple threshold (e.g., max nodes per satellite) configured by the operator
- **AND** calculations remain simple (count-based); no full link budget or orbital mechanics

#### Scenario: Visualize saturation on map
- **WHEN** the satellite footprint layer is enabled
- **THEN** the system optionally colors or labels footprints by saturation status (e.g., highlight saturated footprints)
- **AND** the user can identify which footprints may have too many users
