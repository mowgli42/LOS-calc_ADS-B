// Minimalistic ADS-B LOS Calculator frontend

const REFRESH_INTERVAL_MS = 15 * 60 * 1000; // 15 minutes
let distanceChart = null;
let carriers = {};
let selectedCarriers = new Set();
let carrierRanges = {};
let refreshTimer = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    await loadCarriers();
    setupCarrierSelection();
    setupConfiguration();
    initializeChart();
    initializeGraph();
    initializeGeoGraph();
    await refreshData();
    startAutoRefresh();
});

// Load available carriers from API
async function loadCarriers() {
    try {
        const response = await fetch('/api/carriers');
        carriers = await response.json();
        renderCarrierList();
        initializeCarrierRanges();
    } catch (error) {
        console.error('Error loading carriers:', error);
        updateStatus('Error loading carriers', 'error');
    }
}

// Render carrier selection checkboxes
function renderCarrierList() {
    const container = document.getElementById('carrier-list');
    container.innerHTML = '';
    
    for (const [code, info] of Object.entries(carriers)) {
        const checkbox = document.createElement('div');
        checkbox.className = 'carrier-checkbox';
        checkbox.innerHTML = `
            <input type="checkbox" id="carrier-${code}" value="${code}">
            <label for="carrier-${code}" class="carrier-label">${info.name} (${code})</label>
        `;
        
        checkbox.querySelector('input').addEventListener('change', handleCarrierSelection);
        container.appendChild(checkbox);
    }
}

// Handle carrier selection changes
function handleCarrierSelection(event) {
    const carrier = event.target.value;
    if (event.target.checked) {
        selectedCarriers.add(carrier);
    } else {
        selectedCarriers.delete(carrier);
    }
    updateConfigurationPanel();
    refreshData();
}

// Setup configuration panel
function setupConfiguration() {
    updateConfigurationPanel();
}

function updateConfigurationPanel() {
    const container = document.getElementById('config-panel');
    container.innerHTML = '';
    
    if (selectedCarriers.size === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); font-size: 14px;">Select carriers to configure communication ranges</p>';
        return;
    }
    
    for (const code of Array.from(selectedCarriers).sort()) {
        const info = carriers[code];
        const configItem = document.createElement('div');
        configItem.className = 'config-item';
        configItem.innerHTML = `
            <label for="range-${code}">${info.name} (${code}) - Range (km)</label>
            <input 
                type="number" 
                id="range-${code}" 
                value="${carrierRanges[code] || info.default_range_km}" 
                min="50" 
                max="500" 
                step="10"
            >
        `;
        
        configItem.querySelector('input').addEventListener('change', (e) => {
            carrierRanges[code] = parseFloat(e.target.value);
            refreshData();
        });
        
        container.appendChild(configItem);
    }
}

// Initialize carrier ranges with defaults
function initializeCarrierRanges() {
    for (const [code, info] of Object.entries(carriers)) {
        carrierRanges[code] = info.default_range_km;
    }
}

// Initialize Chart.js bar chart
function initializeChart() {
    const ctx = document.getElementById('distance-chart').getContext('2d');
    
    distanceChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['0-50 km', '50-100 km', '100-150 km', '150-200 km', '200+ km'],
            datasets: [{
                label: 'Aircraft Pairs',
                data: [0, 0, 0, 0, 0],
                backgroundColor: 'rgba(0, 255, 136, 0.6)',
                borderColor: '#00ff88',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(10, 14, 15, 0.9)',
                    titleColor: '#00ff88',
                    bodyColor: '#e0e8e9',
                    borderColor: '#2a3536',
                    borderWidth: 1
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#a0b0b2'
                    },
                    grid: {
                        color: '#2a3536'
                    }
                },
                x: {
                    ticks: {
                        color: '#a0b0b2'
                    },
                    grid: {
                        color: '#2a3536'
                    }
                }
            }
        }
    });
    
    // Initialize connection distribution chart
    const connectionCtx = document.getElementById('connection-chart').getContext('2d');
    connectionChart = new Chart(connectionCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Number of Aircraft',
                data: [],
                backgroundColor: 'rgba(0, 255, 136, 0.3)',
                borderColor: 'rgba(0, 255, 136, 0.8)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(10, 14, 15, 0.95)',
                    titleColor: '#e8e8e8',
                    bodyColor: '#e8e8e8',
                    borderColor: '#00ff88',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            return context.parsed.y + ' aircraft with ' + context.parsed.x + ' connection' + (context.parsed.x !== 1 ? 's' : '');
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Number of Connections',
                        color: '#e8e8e8'
                    },
                    ticks: {
                        color: '#b0b0b0',
                        stepSize: 1
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Number of Aircraft',
                        color: '#e8e8e8'
                    },
                    ticks: {
                        color: '#b0b0b0',
                        beginAtZero: true
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    }
                }
            }
        }
    });
}

// Refresh all data
async function refreshData() {
    if (selectedCarriers.size === 0) {
        updateChart([0, 0, 0, 0, 0]);
        updateStats({ direct: 0, '1hop': 0, '2hop': 0, '3hop': 0 });
        return;
    }
    
    updateStatus('Refreshing...', 'loading');
    
    try {
        const carriersArray = Array.from(selectedCarriers);
        const rangesObj = {};
        carriersArray.forEach(code => {
            rangesObj[code] = carrierRanges[code] || carriers[code].default_range_km;
        });
        
        // Fetch distances and communication stats in parallel
        const [distancesResp, commResp] = await Promise.all([
            fetch('/api/distances', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    carriers: carriersArray,
                    carrier_ranges: rangesObj
                })
            }),
            fetch('/api/communication', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    carriers: carriersArray,
                    carrier_ranges: rangesObj
                })
            })
        ]);
        
        const distancesData = await distancesResp.json();
        const commData = await commResp.json();
        
        if (distancesResp.ok && commResp.ok) {
            // Update chart
            const binData = [
                distancesData.bins['0-50'] || 0,
                distancesData.bins['50-100'] || 0,
                distancesData.bins['100-150'] || 0,
                distancesData.bins['150-200'] || 0,
                distancesData.bins['200-inf'] || 0
            ];
            updateChart(binData);
            
            // Update statistics
            updateStats(commData);
            
            // Update graphs
            updateGraph();
            updateGeoGraph();
            
            // Update connection distribution chart
            updateConnectionChart(graphData);
            
            // Update status
            const lastUpdate = distancesData.last_update 
                ? new Date(distancesData.last_update).toLocaleTimeString()
                : 'Unknown';
            updateStatus(`Last updated: ${lastUpdate} | ${distancesData.aircraft_count} aircraft`, 'success');
        } else {
            throw new Error('API error');
        }
        
    } catch (error) {
        console.error('Error refreshing data:', error);
        updateStatus('Error loading data', 'error');
    }
}

// Update chart data
function updateChart(data) {
    if (!distanceChart) {
        initializeChart();
    }
    if (distanceChart) {
        distanceChart.data.datasets[0].data = data;
        distanceChart.update('none');
    }
}

// Calculate and update connection distribution chart
function updateConnectionChart(graphData) {
    if (!graphData || !graphData.nodes || !graphData.edges) {
        return;
    }
    
    if (!connectionChart) {
        initializeChart();
    }
    
    // Calculate connection count (degree) for each node
    const connectionCounts = new Map();
    
    // Initialize all nodes with 0 connections
    graphData.nodes.forEach(node => {
        connectionCounts.set(node.id, 0);
    });
    
    // Count connections for each node
    graphData.edges.forEach(edge => {
        const from = connectionCounts.get(edge.from) || 0;
        const to = connectionCounts.get(edge.to) || 0;
        connectionCounts.set(edge.from, from + 1);
        connectionCounts.set(edge.to, to + 1);
    });
    
    // Create distribution: count how many aircraft have 0, 1, 2, etc. connections
    const connectionValues = Array.from(connectionCounts.values());
    if (connectionValues.length === 0) {
        // No nodes, clear chart
        if (connectionChart) {
            connectionChart.data.labels = [];
            connectionChart.data.datasets[0].data = [];
            connectionChart.update('none');
        }
        return;
    }
    
    const maxConnections = Math.max(...connectionValues);
    const distribution = new Array(maxConnections + 1).fill(0);
    
    connectionCounts.forEach(count => {
        distribution[count]++;
    });
    
    // Create labels and data for chart
    const labels = distribution.map((_, index) => index.toString());
    const data = distribution;
    
    // Update chart
    if (connectionChart) {
        connectionChart.data.labels = labels;
        connectionChart.data.datasets[0].data = data;
        connectionChart.update('none');
    }
}

// Update communication statistics
function updateStats(stats) {
    document.getElementById('stat-direct').textContent = stats.direct || 0;
    document.getElementById('stat-1hop').textContent = stats['1hop'] || 0;
    document.getElementById('stat-2hop').textContent = stats['2hop'] || 0;
    document.getElementById('stat-3hop').textContent = stats['3hop'] || 0;
}

// Update status indicator
function updateStatus(text, type = 'info') {
    const statusText = document.getElementById('status-text');
    const statusIcon = document.querySelector('.status-icon');
    
    statusText.textContent = text;
    
    if (type === 'error') {
        statusIcon.style.color = '#ff4444';
    } else if (type === 'loading') {
        statusIcon.style.color = '#ffaa00';
    } else {
        statusIcon.style.color = '#00cc6f';
    }
}

// Start automatic refresh timer
function startAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    
    refreshTimer = setInterval(() => {
        refreshData();
    }, REFRESH_INTERVAL_MS);
}

// Graph visualization
let graphSimulation = null;
let graphSvg = null;
let graphTooltip = null;

// Geospatial graph visualization
let geoGraphSvg = null;
let geoGraphProjection = null;
let geoGraphTooltip = null;

// Initialize graph visualization
function initializeGraph() {
    const container = document.getElementById('graph-container');
    graphSvg = d3.select('#graph-svg');
    
    // Create tooltip
    graphTooltip = d3.select('body').append('div')
        .attr('class', 'graph-tooltip')
        .style('opacity', 0);
}

// Initialize geospatial graph visualization
function initializeGeoGraph() {
    geoGraphSvg = d3.select('#geo-graph-svg');
    
    // Create tooltip
    geoGraphTooltip = d3.select('body').append('div')
        .attr('class', 'graph-tooltip')
        .style('opacity', 0);
}

// Update graph visualization
async function updateGraph() {
    if (selectedCarriers.size === 0) {
        if (graphSvg) {
            graphSvg.selectAll('*').remove();
        }
        return;
    }
    
    try {
        const carriersArray = Array.from(selectedCarriers);
        const rangesObj = {};
        carriersArray.forEach(code => {
            rangesObj[code] = carrierRanges[code] || carriers[code].default_range_km;
        });
        
        const response = await fetch('/api/graph', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                carriers: carriersArray,
                carrier_ranges: rangesObj
            })
        });
        
        if (!response.ok) {
            return;
        }
        
        const graphData = await response.json();
        
        if (!graphData.nodes || graphData.nodes.length === 0) {
            if (graphSvg) {
                graphSvg.selectAll('*').remove();
            }
            return;
        }
        
        renderGraph(graphData);
        
        // Update connection distribution chart
        updateConnectionChart(graphData);
        
    } catch (error) {
        console.error('Error loading graph data:', error);
    }
}

// Render graph using D3.js force simulation
function renderGraph(data) {
    if (!graphSvg) {
        initializeGraph();
    }
    
    // Clear previous graph
    graphSvg.selectAll('*').remove();
    
    const width = graphSvg.node().getBoundingClientRect().width || 800;
    const height = graphSvg.node().getBoundingClientRect().height || 500;
    
    // Create a container group for zoom/pan transformations
    const container = graphSvg.append('g')
        .attr('class', 'graph-container-group');
    
    // Set up zoom behavior
    const zoom = d3.zoom()
        .scaleExtent([0.1, 4]) // Allow zoom from 0.1x to 4x
        .on('zoom', (event) => {
            container.attr('transform', event.transform);
        });
    
    // Apply zoom behavior to the SVG
    graphSvg.call(zoom);
    
    // Calculate distance range for edge thickness mapping
    const distances = data.edges.map(e => e.distance);
    const minDistance = distances.length > 0 ? Math.min(...distances) : 0;
    const maxDistance = distances.length > 0 ? Math.max(...distances) : 1;
    const distanceRange = maxDistance - minDistance || 1;
    
    // Convert edges from {from, to, distance} to {source, target, distance} for D3
    // Create a node map for fast lookup
    const nodeMap = new Map(data.nodes.map(n => [n.id, n]));
    const d3Edges = data.edges.map(e => ({
        source: nodeMap.get(e.from),
        target: nodeMap.get(e.to),
        distance: e.distance
    })).filter(e => e.source && e.target); // Filter out any invalid edges
    
    // Create force simulation
    if (graphSimulation) {
        graphSimulation.stop();
    }
    
    graphSimulation = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(d3Edges).id(d => d.id).distance(d => d.distance * 2))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(20));
    
    // Create edges (lines) - inside the container group
    const edges = container.append('g')
        .attr('class', 'edges')
        .selectAll('line')
        .data(d3Edges)
        .enter()
        .append('line')
        .attr('class', 'graph-edge')
        .attr('stroke-width', d => {
            // Inverse mapping: shorter distance = thicker line
            // Normalize distance (0-1 range, inverted)
            const normalized = 1 - ((d.distance - minDistance) / distanceRange);
            // Map to thickness range: 1px to 8px
            return 1 + (normalized * 7);
        })
        .on('mouseover', function(event, d) {
            graphTooltip.transition()
                .duration(200)
                .style('opacity', 0.9);
            const distance = typeof d.distance === 'number' ? d.distance : (d.distance || 0);
            graphTooltip.html(`Distance: ${distance.toFixed(2)} km`)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 10) + 'px')
                .style('display', 'block');
            
            d3.select(this).attr('stroke-opacity', 1);
        })
        .on('mouseout', function() {
            graphTooltip.transition()
                .duration(500)
                .style('opacity', 0)
                .style('display', 'none');
            
            d3.select(this).attr('stroke-opacity', 0.6);
        });
    
    // Create nodes (circles) - inside the container group
    const nodes = container.append('g')
        .attr('class', 'nodes')
        .selectAll('circle')
        .data(data.nodes, d => d.id)
        .enter()
        .append('circle')
        .attr('class', 'graph-node')
        .attr('r', 8)
        .attr('fill', d => {
            // Use green tint for nodes
            return 'rgba(0, 255, 136, 0.8)';
        })
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag', dragged)
            .on('end', dragEnded))
        .on('mouseover', function(event, d) {
            graphTooltip.transition()
                .duration(200)
                .style('opacity', 0.9);
            graphTooltip.html(`${d.label}<br/>${d.carrier || 'Unknown'}`)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 10) + 'px')
                .style('display', 'block');
        })
        .on('mouseout', function() {
            graphTooltip.transition()
                .duration(500)
                .style('opacity', 0)
                .style('display', 'none');
        });
    
    // Add labels - inside the container group
    const labels = container.append('g')
        .attr('class', 'labels')
        .selectAll('text')
        .data(data.nodes, d => d.id)
        .enter()
        .append('text')
        .attr('class', 'graph-node-label')
        .text(d => d.label.length > 8 ? d.label.substring(0, 8) + '...' : d.label)
        .attr('dx', 0)
        .attr('dy', 15);
    
    // Initial zoom to fit the graph (after a short delay to allow simulation to start)
    setTimeout(() => {
        if (graphSimulation && data.nodes.length > 0) {
            // Get bounding box of all nodes
            const bounds = { 
                minX: Infinity, maxX: -Infinity, 
                minY: Infinity, maxY: -Infinity 
            };
            data.nodes.forEach(node => {
                if (node.x !== undefined && node.y !== undefined) {
                    bounds.minX = Math.min(bounds.minX, node.x);
                    bounds.maxX = Math.max(bounds.maxX, node.x);
                    bounds.minY = Math.min(bounds.minY, node.y);
                    bounds.maxY = Math.max(bounds.maxY, node.y);
                }
            });
            
            // Calculate padding and scale
            const padding = 50;
            const graphWidth = bounds.maxX - bounds.minX || 1;
            const graphHeight = bounds.maxY - bounds.minY || 1;
            const scale = Math.min(
                (width - padding * 2) / graphWidth,
                (height - padding * 2) / graphHeight,
                1.0 // Don't zoom in, only out to fit
            );
            
            // Center the graph
            const centerX = (bounds.minX + bounds.maxX) / 2;
            const centerY = (bounds.minY + bounds.maxY) / 2;
            const translateX = width / 2 - centerX * scale;
            const translateY = height / 2 - centerY * scale;
            
            // Apply initial transform
            const transform = d3.zoomIdentity
                .translate(translateX, translateY)
                .scale(scale);
            
            graphSvg.transition()
                .duration(750)
                .call(zoom.transform, transform);
        }
    }, 500);
    
    // Update positions on tick
    graphSimulation.on('tick', () => {
        edges
            .attr('x1', d => {
                // Handle both object and index references
                const source = typeof d.source === 'object' ? d.source : data.nodes[d.source];
                return source ? source.x : 0;
            })
            .attr('y1', d => {
                const source = typeof d.source === 'object' ? d.source : data.nodes[d.source];
                return source ? source.y : 0;
            })
            .attr('x2', d => {
                const target = typeof d.target === 'object' ? d.target : data.nodes[d.target];
                return target ? target.x : 0;
            })
            .attr('y2', d => {
                const target = typeof d.target === 'object' ? d.target : data.nodes[d.target];
                return target ? target.y : 0;
            });
        
        nodes
            .attr('cx', d => d.x || 0)
            .attr('cy', d => d.y || 0);
        
        labels
            .attr('x', d => d.x || 0)
            .attr('y', d => d.y || 0);
    });
}

// Drag handlers for nodes
function dragStarted(event, d) {
    if (!event.active && graphSimulation) graphSimulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}

function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
}

function dragEnded(event, d) {
    if (!event.active && graphSimulation) graphSimulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
}

// Update geospatial graph visualization
async function updateGeoGraph() {
    if (selectedCarriers.size === 0) {
        if (geoGraphSvg) {
            geoGraphSvg.selectAll('*').remove();
        }
        return;
    }
    
    try {
        const carriersArray = Array.from(selectedCarriers);
        const rangesObj = {};
        carriersArray.forEach(code => {
            rangesObj[code] = carrierRanges[code] || carriers[code].default_range_km;
        });
        
        const response = await fetch('/api/graph', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                carriers: carriersArray,
                carrier_ranges: rangesObj
            })
        });
        
        if (!response.ok) {
            return;
        }
        
        const graphData = await response.json();
        
        if (!graphData.nodes || graphData.nodes.length === 0) {
            if (geoGraphSvg) {
                geoGraphSvg.selectAll('*').remove();
            }
            return;
        }
        
        // Filter out nodes without valid coordinates
        const validNodes = graphData.nodes.filter(n => 
            n.latitude != null && n.longitude != null &&
            !isNaN(n.latitude) && !isNaN(n.longitude)
        );
        
        if (validNodes.length === 0) {
            if (geoGraphSvg) {
                geoGraphSvg.selectAll('*').remove();
            }
            return;
        }
        
        renderGeoGraph(graphData, validNodes);
        
    } catch (error) {
        console.error('Error loading geospatial graph data:', error);
    }
}

// Render geospatial graph using D3.js geographic projection
function renderGeoGraph(data, validNodes) {
    if (!geoGraphSvg) {
        initializeGeoGraph();
    }
    
    // Clear previous graph
    geoGraphSvg.selectAll('*').remove();
    
    const width = geoGraphSvg.node().getBoundingClientRect().width || 800;
    const height = geoGraphSvg.node().getBoundingClientRect().height || 500;
    
    // Calculate bounding box of valid coordinates
    const lats = validNodes.map(n => n.latitude);
    const lons = validNodes.map(n => n.longitude);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);
    
    // Calculate center and extent with padding
    const centerLon = (minLon + maxLon) / 2;
    const centerLat = (minLat + maxLat) / 2;
    const latRange = maxLat - minLat || 1;
    const lonRange = maxLon - minLon || 1;
    const padding = 0.1; // 10% padding
    
    // Create Mercator projection
    geoGraphProjection = d3.geoMercator()
        .center([centerLon, centerLat])
        .scale(Math.min(
            width / lonRange / (Math.PI / 180) / Math.cos(centerLat * Math.PI / 180),
            height / latRange / (Math.PI / 180)
        ) * 0.9)
        .translate([width / 2, height / 2]);
    
    // Create a container group for zoom/pan transformations
    const container = geoGraphSvg.append('g')
        .attr('class', 'geo-graph-container-group');
    
    // Set up zoom behavior
    const zoom = d3.zoom()
        .scaleExtent([0.1, 10])
        .on('zoom', (event) => {
            container.attr('transform', event.transform);
        });
    
    // Apply zoom behavior to the SVG
    geoGraphSvg.call(zoom);
    
    // Convert edges to use valid nodes only and convert coordinates
    const validNodeMap = new Map(validNodes.map(n => [n.id, n]));
    const nodeCoords = new Map(validNodes.map(n => [
        n.id,
        geoGraphProjection([n.longitude, n.latitude])
    ]));
    
    // Calculate distance range for edge thickness (same as regular graph)
    const distances = data.edges.map(e => e.distance);
    const minDistance = distances.length > 0 ? Math.min(...distances) : 0;
    const maxDistance = distances.length > 0 ? Math.max(...distances) : 1;
    const distanceRange = maxDistance - minDistance || 1;
    
    // Filter edges to only include valid nodes
    const validEdges = data.edges.filter(e => 
        validNodeMap.has(e.from) && validNodeMap.has(e.to)
    );
    
    // Create edges (lines) using geographic coordinates
    const edges = container.append('g')
        .attr('class', 'edges')
        .selectAll('line')
        .data(validEdges)
        .enter()
        .append('line')
        .attr('class', 'graph-edge')
        .attr('x1', d => {
            const coords = nodeCoords.get(d.from);
            return coords ? coords[0] : 0;
        })
        .attr('y1', d => {
            const coords = nodeCoords.get(d.from);
            return coords ? coords[1] : 0;
        })
        .attr('x2', d => {
            const coords = nodeCoords.get(d.to);
            return coords ? coords[0] : 0;
        })
        .attr('y2', d => {
            const coords = nodeCoords.get(d.to);
            return coords ? coords[1] : 0;
        })
        .attr('stroke-width', d => {
            // Same thickness calculation as regular graph: shorter distance = thicker line
            const normalized = 1 - ((d.distance - minDistance) / distanceRange);
            return 1 + (normalized * 7); // 1px to 8px
        })
        .on('mouseover', function(event, d) {
            geoGraphTooltip.transition()
                .duration(200)
                .style('opacity', 0.9);
            geoGraphTooltip.html(`Distance: ${d.distance.toFixed(2)} km`)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 10) + 'px')
                .style('display', 'block');
            
            d3.select(this).attr('stroke-opacity', 1);
        })
        .on('mouseout', function() {
            geoGraphTooltip.transition()
                .duration(500)
                .style('opacity', 0)
                .style('display', 'none');
            
            d3.select(this).attr('stroke-opacity', 0.6);
        });
    
    // Create nodes (circles) at geographic coordinates
    const nodes = container.append('g')
        .attr('class', 'nodes')
        .selectAll('circle')
        .data(validNodes)
        .enter()
        .append('circle')
        .attr('class', 'graph-node')
        .attr('r', 8)
        .attr('cx', d => {
            const coords = geoGraphProjection([d.longitude, d.latitude]);
            return coords ? coords[0] : 0;
        })
        .attr('cy', d => {
            const coords = geoGraphProjection([d.longitude, d.latitude]);
            return coords ? coords[1] : 0;
        })
        .attr('fill', 'rgba(0, 255, 136, 0.8)')
        .on('mouseover', function(event, d) {
            geoGraphTooltip.transition()
                .duration(200)
                .style('opacity', 0.9);
            geoGraphTooltip.html(`${d.label}<br/>${d.carrier || 'Unknown'}<br/>${d.latitude.toFixed(4)}°, ${d.longitude.toFixed(4)}°`)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 10) + 'px')
                .style('display', 'block');
        })
        .on('mouseout', function() {
            geoGraphTooltip.transition()
                .duration(500)
                .style('opacity', 0)
                .style('display', 'none');
        });
    
    // Add labels
    const labels = container.append('g')
        .attr('class', 'labels')
        .selectAll('text')
        .data(validNodes)
        .enter()
        .append('text')
        .attr('class', 'graph-node-label')
        .text(d => d.label.length > 8 ? d.label.substring(0, 8) + '...' : d.label)
        .attr('x', d => {
            const coords = geoGraphProjection([d.longitude, d.latitude]);
            return coords ? coords[0] : 0;
        })
        .attr('y', d => {
            const coords = geoGraphProjection([d.longitude, d.latitude]);
            return coords ? coords[1] + 15 : 0;
        })
        .attr('text-anchor', 'middle');
}

// Handle window resize
window.addEventListener('resize', () => {
    if (graphSimulation && graphSvg) {
        const width = graphSvg.node().getBoundingClientRect().width || 800;
        const height = graphSvg.node().getBoundingClientRect().height || 500;
        graphSimulation.force('center', d3.forceCenter(width / 2, height / 2));
        graphSimulation.alpha(0.3).restart();
    }
    
    // Update geospatial graph projection on resize
    if (geoGraphSvg && geoGraphProjection) {
        const width = geoGraphSvg.node().getBoundingClientRect().width || 800;
        const height = geoGraphSvg.node().getBoundingClientRect().height || 500;
        // Re-render on resize
        updateGeoGraph();
    }
});

