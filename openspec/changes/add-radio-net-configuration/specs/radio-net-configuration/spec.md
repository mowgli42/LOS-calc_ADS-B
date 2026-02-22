# Radio Net Configuration

## ADDED Requirements

### Requirement: Per-Node Data Capture
The system SHALL capture configuration data for each radio/node beyond frequency band alone.

#### Scenario: Capture full node configuration
- **WHEN** a node (radio) is registered or configured
- **THEN** the system stores: node identifier, configured nets (which nets the radio is set up to join), frequency capability (supported bands), assignment (which net(s) the node is assigned to)
- **AND** the system distinguishes between configured nets (radio has the channel) and assigned nets (operator expects the radio on that net)

#### Scenario: Report per-node net status
- **WHEN** a user requests node data for a net or all nodes
- **THEN** the system returns for each node: configured nets, assigned nets, and whether the node is compliant (assigned nets ⊆ configured nets)

### Requirement: Net Definition and Identification
The system SHALL define nets by name and frequency (not just band) and identify which nets exist.

#### Scenario: Define a net
- **WHEN** a user creates or updates a net
- **THEN** the system stores: net identifier, net name, frequency (e.g., MHz), band (e.g., VHF, UHF), and optional description
- **AND** the system allows multiple nets to be defined

#### Scenario: List nets with participants
- **WHEN** a user requests net information
- **THEN** the system returns each net with its frequency, band, and list of nodes configured to join that net
- **AND** the system returns which nodes are assigned to the net

### Requirement: Net Connectivity
The system SHALL identify which nets are connected (can share traffic via bridge nodes).

#### Scenario: Detect connected nets via shared participants
- **WHEN** two or more nets share at least one node configured to join both
- **THEN** the system identifies those nets as connected
- **AND** the system reports the set of connected net groups (net A connected to B, B to C implies A, B, C are in one connected group)

#### Scenario: Report net connectivity graph
- **WHEN** a user requests net connectivity
- **THEN** the system returns which nets are connected and which nodes bridge them
- **AND** the system supports visualization of net-to-net connectivity

### Requirement: Non-Compliant Radio Identification
The system SHALL identify radios that are not set up to join their assigned net(s).

#### Scenario: Identify radios missing net configuration
- **WHEN** a node is assigned to a net but is not configured to join that net
- **THEN** the system flags the node as non-compliant for that net
- **AND** the system lists all nodes that are not configured to join at least one of their assigned nets

#### Scenario: Report compliance status per net
- **WHEN** a user requests compliance for a net
- **THEN** the system returns: nodes configured and assigned (compliant), nodes assigned but not configured (non-compliant), nodes configured but not assigned (optional/spare)
- **AND** the system supports filtering or highlighting non-compliant nodes in the UI
