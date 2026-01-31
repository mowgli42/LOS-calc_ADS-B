## Context
This system ingests real-time aircraft ADS-B data from the OpenSky Network API, calculates line-of-sight distances between aircraft using radio horizon calculations, and analyzes multi-hop communication paths. The web interface allows users to filter by carrier and visualize distance distributions and connectivity statistics.

## Goals / Non-Goals

### Goals
- Simple, minimalistic implementation with clean code structure
- Real-time aircraft data ingestion from OpenSky Network API (refreshed every 15 minutes)
- Accurate radio horizon line-of-sight distance calculations accounting for Earth curvature and altitude
- Multi-hop communication path analysis (up to 3 hops)
- Minimalistic web interface with dark theme, green tints, and small icons
- Carrier filtering for top 25 worldwide airlines
- Carrier-specific communication range thresholds
- Automatic data refresh every 15 minutes

### Non-Goals
- Persistent data storage or historical analysis (real-time only)
- Aircraft identification beyond carrier filtering
- Flight path prediction or trajectory analysis
- Real-time map visualization (focus on statistics and graphs)
- Multi-user authentication or session management
- Deployment configuration or production optimizations (development focus)

## Decisions

### Decision: Radio Horizon Calculation Method
**What**: Use radio horizon formula `d = sqrt(2 * R * h1) + sqrt(2 * R * h2)` where R is Earth radius and h1, h2 are aircraft altitudes.

**Why**: Radio horizon accounts for Earth's curvature and altitude, providing realistic line-of-sight distance that radio signals can travel. This is more accurate than simple 3D Euclidean distance for communication range estimation.

**Alternatives considered**:
- Great circle distance only: Ignores altitude, less accurate for communication
- Simple 3D Euclidean distance: Doesn't account for Earth curvature, overestimates range
- Radio horizon with atmospheric refraction correction: More complex, minimal improvement for aircraft-to-aircraft scenarios

### Decision: Python Flask Backend with HTML/JS Frontend
**What**: Use Python Flask for backend API, simple HTML/CSS/JavaScript for frontend (no React/Vue framework). Keep implementation simple and minimalistic.

**Why**: Minimal dependencies, easy to deploy, sufficient for the required functionality. No need for complex state management or component frameworks given the straightforward UI requirements. Simple implementation reduces maintenance burden and improves readability.

**Alternatives considered**:
- Full-stack Node.js: Python better for scientific calculations
- React/Vue frontend: Adds unnecessary complexity for simple interface
- Django: Heavier framework than needed for API-only backend

### Decision: Minimalistic Dark UI with Green Tints
**What**: Design a minimalistic web interface with dark background theme, green accent colors, and small icons for visual elements.

**Why**: Dark theme reduces eye strain and provides a modern, technical aesthetic. Green tints align with aviation/monitoring interfaces and provide clear visual hierarchy. Small icons keep the interface uncluttered while maintaining usability. Minimalistic design emphasizes data over decoration.

**Alternatives considered**:
- Light theme: More common but less suited for technical monitoring displays
- Multiple accent colors: Adds visual complexity, green alone provides sufficient contrast
- Large icons/buttons: Takes up more screen space, less minimalistic

### Decision: Top 25 Worldwide Carriers
**What**: Support carrier filtering for the top 25 airlines worldwide by fleet size/operations, including major carriers like American Airlines (AAL), Delta (DAL), United (UAL), Southwest (SWA), Lufthansa (DLH), British Airways (BAW), Air France (AFR), Emirates (UAE), etc.

**Why**: Top 25 carriers represent the majority of commercial aircraft traffic globally, providing comprehensive coverage while keeping the interface manageable. This addresses the scale needed for meaningful analysis without overwhelming users with hundreds of carriers.

**Alternatives considered**:
- All carriers: Too many options, cluttered interface
- Top 10 only: Limited coverage, may miss significant traffic
- Regional filtering: Adds complexity, top 25 provides global coverage

### Decision: Carrier-Specific Communication Range
**What**: Each carrier has its own configurable communication range threshold based on their aircraft capabilities and operational parameters.

**Why**: Different carriers operate different aircraft types with varying communication equipment capabilities. Carrier-specific ranges provide more accurate connectivity analysis than a single global threshold.

**Alternatives considered**:
- Global communication range: Simpler but less accurate for diverse fleet capabilities
- Aircraft-type-specific ranges: Too granular, carrier-level is sufficient

### Decision: 15-Minute Refresh Interval
**What**: Automatically refresh aircraft data every 15 minutes (900 seconds).

**Why**: Balances data freshness with API usage and server load. 15 minutes provides reasonably current data while reducing API calls significantly compared to real-time updates. Sufficient for trend analysis and operational monitoring without excessive resource consumption.

**Alternatives considered**:
- 30 seconds: Too frequent, high API usage, unnecessary for monitoring use case
- 1 hour: Too infrequent, data becomes stale
- User-configurable: Adds complexity, 15 minutes is a reasonable default for most use cases

### Decision: Breadth-First Search for Multi-Hop Analysis
**What**: Use BFS graph traversal to find paths of different hop lengths.

**Why**: BFS naturally finds shortest paths and can be limited to specific depths (1-hop, 2-hop, 3-hop). Efficient for sparse graphs (aircraft networks).

**Alternatives considered**:
- Depth-First Search: Doesn't guarantee shortest paths
- Floyd-Warshall all-pairs shortest path: O(n³) complexity, overkill for depth-limited queries
- Dijkstra's algorithm: More complex than needed for unweighted graph

### Decision: OpenSky Network API
**What**: Use public OpenSky Network API (`https://opensky-network.org/api/states/all`) for ADS-B data.

**Why**: Free, public API providing real-time aircraft state vectors. No authentication required for basic access. Well-documented.

**Alternatives considered**:
- ADSBExchange API: Requires API key, potentially higher rate limits
- Custom ADS-B receiver: Requires hardware, more complex setup
- Simulated data: Doesn't provide real-world value

### Decision: Distance Binning Strategy
**What**: Use fixed bins (0-50km, 50-100km, 100-150km, 150-200km, 200km+) for bar graph visualization.

**Why**: Provides clear visualization of distance distribution. Fixed bins make comparison across refreshes consistent.

**Alternatives considered**:
- Dynamic binning based on data range: More complex, less consistent
- Logarithmic bins: Better for wide ranges but harder to interpret
- Percentile-based bins: Requires sorting all distances, less intuitive

## Risks / Trade-offs

### Risk: OpenSky API Rate Limiting
**Mitigation**: Implement caching layer to reduce API calls. Respect rate limits (typically 400 requests per 10 seconds for unauthenticated access).

### Risk: Large Number of Aircraft Pairs
**Trade-off**: O(n²) complexity for distance calculations. For typical airspace (~100-500 aircraft), this is manageable. If scaling to thousands, consider spatial indexing (R-tree) or distance thresholds.

**Mitigation**: Calculate only distances for selected carriers, reducing n significantly.

### Risk: Missing or Invalid Aircraft Data
**Mitigation**: Validate altitude and position data before calculations. Skip invalid entries with logging.

### Risk: Graph Analysis Performance with Large Networks
**Mitigation**: Limit to 3 hops maximum. BFS with depth limit is efficient. Consider timeout for very large networks.

## Migration Plan
N/A - This is a new capability with no existing system to migrate from.

## Open Questions
- None - all questions resolved: Top 25 carriers supported, carrier-specific communication ranges, 15-minute refresh interval

