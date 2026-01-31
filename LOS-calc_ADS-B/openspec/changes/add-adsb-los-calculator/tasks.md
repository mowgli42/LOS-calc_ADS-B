## 1. Backend Implementation
- [x] 1.1 Create simple Flask application structure (`app.py`)
- [x] 1.2 Create configuration module (`config.py`) with top 25 carrier ICAO codes and carrier-specific communication range defaults
- [x] 1.3 Implement OpenSky API client (`data_ingester.py`)
- [x] 1.4 Implement radio horizon distance calculator (`distance_calculator.py`)
- [x] 1.5 Implement communication graph analyzer (`communication_analyzer.py`) supporting carrier-specific ranges
- [x] 1.6 Create REST API endpoints (`/api/aircraft`, `/api/distances`, `/api/communication`)
- [x] 1.7 Add data caching and 15-minute automatic refresh mechanism
- [x] 1.8 Create `requirements.txt` with minimal dependencies
- [x] 1.9 Update communication statistics to use only carrier-specific communication ranges (remove geometric LOS requirement)
- [x] 1.10 Create API endpoint to return network graph data structure with nodes (aircraft) and edges (connections) with distance information

## 2. Frontend Implementation
- [x] 2.1 Create minimalistic HTML template (`templates/index.html`)
- [x] 2.2 Create CSS styling with dark theme, green tints, and small icons (`static/css/style.css`)
- [x] 2.3 Implement simple JavaScript data fetching (`static/js/main.js`)
- [x] 2.4 Implement Chart.js bar graph rendering with dark theme styling
- [x] 2.5 Add carrier selection UI components for top 25 worldwide carriers with small icons
- [x] 2.6 Add minimalistic communication statistics display with green-tinted highlights
- [x] 2.7 Implement 15-minute auto-refresh timer
- [x] 2.8 Add configuration panel for carrier-specific communication range inputs
- [x] 2.9 Add network graph visualization component showing aircraft connections using D3.js force-directed layout
- [x] 2.10 Implement edge thickness mapping in network graph where thicker edges represent shorter distances (inverse relationship)
- [x] 2.11 Style network graph visualization to match dark theme with green tints
- [x] 2.12 Add interactive features to network graph (hover tooltips showing distance, draggable nodes, responsive layout)

## 3. Testing & Validation
- [x] 3.1 Test OpenSky API integration with rate limiting
- [x] 3.2 Validate distance calculations against known test cases
- [x] 3.3 Test graph analysis algorithms with carrier-specific ranges
- [x] 3.4 Verify minimalistic dark UI with green tints displays correctly
- [x] 3.5 Test 15-minute automatic refresh functionality
- [x] 3.6 Verify top 25 carrier filtering works correctly
- [ ] 3.7 Test network graph visualization with various numbers of selected aircraft
- [ ] 3.8 Verify edge thickness in network graph correctly represents distance relationships

## 4. Documentation
- [x] 4.1 Add inline code comments
- [x] 4.2 Create README with setup instructions
- [x] 4.3 Document API endpoints

