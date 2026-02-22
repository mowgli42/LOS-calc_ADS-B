// Minimalistic ADS-B LOS Calculator frontend

const REFRESH_INTERVAL_MS = 15 * 60 * 1000; // 15 minutes
let distanceChart = null;
let connectionChart = null;
let carriers = {};
let selectedCarriers = new Set();
let carrierRanges = {};
let refreshTimer = null;
let map = null;
let aircraftMarkers = [];
let losLines = [];
let includeAirports = true;
let satelliteFootprintLayer = null;
let satelliteFootprintsEnabled = false;
let lastGraphData = null; // Store last graph data for status checks // Default: airports enabled

// Debug logging utility
const DEBUG_ENABLED = false; // Set to true to enable debug logging
const DEBUG_SERVER_ENDPOINT = 'http://127.0.0.1:7243/ingest/dd47ac53-fdbf-4dc6-8d0b-e0345b1c622a';

function debugLog(location, message, data = {}, hypothesisId = '') {
    if (!DEBUG_ENABLED) return;
    
    const logEntry = {
        location: location,
        message: message,
        data: data,
        timestamp: Date.now(),
        sessionId: 'debug-session',
        runId: 'run1',
        hypothesisId: hypothesisId
    };
    
    // Send log via fetch (non-blocking)
    fetch(DEBUG_SERVER_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(logEntry)
    }).catch(() => {
        // Silently fail if logging server is not available
    });
}

// Radio Net Configuration state and functions
let radioNets = [];
let radioNodes = [];

async function loadRadioNets() {
    try {
        const r = await fetch('/api/radio-nets');
        const data = await r.json();
        radioNets = data.nets || [];
        renderRadioNetList();
        await loadRadioNetConnectivity();
    } catch (e) {
        console.error('Error loading radio nets:', e);
    }
}

async function loadRadioNodes() {
    try {
        const r = await fetch('/api/radio-nodes');
        const data = await r.json();
        radioNodes = data.nodes || [];
        renderRadioNodeList();
        await loadRadioNetNonCompliant();
    } catch (e) {
        console.error('Error loading radio nodes:', e);
    }
}

function renderRadioNetList() {
    const container = document.getElementById('radio-net-list');
    if (!container) return;
    container.innerHTML = '';
    radioNets.forEach(net => {
        const div = document.createElement('div');
        div.className = 'radio-net-item';
        div.innerHTML = `
            <div>
                <strong>${escapeHtml(net.name)}</strong>
                <span style="font-size: 12px; color: var(--text-secondary); margin-left: 8px;">
                    ${net.frequency_mhz} MHz ${net.band}
                </span>
            </div>
            <div class="item-actions">
                <button type="button" class="btn btn-secondary btn-edit-net" data-id="${net.id}">Edit</button>
                <button type="button" class="btn btn-danger btn-delete-net" data-id="${net.id}">Delete</button>
            </div>
        `;
        div.querySelector('.btn-edit-net').addEventListener('click', () => openNetModal(net.id));
        div.querySelector('.btn-delete-net').addEventListener('click', () => deleteNet(net.id));
        container.appendChild(div);
    });
}

function renderRadioNodeList() {
    const container = document.getElementById('radio-node-list');
    if (!container) return;
    const compliance = window.radioCompliance || { per_node: {} };
    container.innerHTML = '';
    radioNodes.forEach(node => {
        const nc = compliance.per_node[node.id] || {};
        const div = document.createElement('div');
        div.className = 'radio-net-item' + (nc.compliant === false ? ' non-compliant' : '');
        div.innerHTML = `
            <div>
                <strong>${escapeHtml(node.label)}</strong>
                <span style="font-size: 11px; color: var(--text-secondary); display: block;">
                    configured: ${(node.configured_nets || []).length} | assigned: ${(node.assigned_nets || []).length}
                    ${nc.missing_nets?.length ? ' ⚠ missing ' + nc.missing_nets.length : ''}
                </span>
            </div>
            <div class="item-actions">
                <button type="button" class="btn btn-secondary btn-edit-node" data-id="${node.id}">Edit</button>
                <button type="button" class="btn btn-danger btn-delete-node" data-id="${node.id}">Delete</button>
            </div>
        `;
        div.querySelector('.btn-edit-node').addEventListener('click', () => openNodeModal(node.id));
        div.querySelector('.btn-delete-node').addEventListener('click', () => deleteNode(node.id));
        container.appendChild(div);
    });
}

function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
}

async function loadRadioNetConnectivity() {
    const container = document.getElementById('radio-net-connectivity');
    if (!container) return;
    try {
        const r = await fetch('/api/radio-nets/connectivity');
        const data = await r.json();
        const groups = data.connected_groups || [];
        const bridges = data.bridge_nodes || [];
        if (groups.length === 0 && bridges.length === 0) {
            container.innerHTML = '<p class="radio-net-help">No nets or no shared nodes.</p>';
            return;
        }
        let html = '';
        if (groups.length > 0) {
            html += '<p><strong>Connected groups:</strong></p><ul style="margin-bottom: 12px;">';
            groups.forEach((g, i) => {
                const names = g.map(nid => {
                    const n = radioNets.find(x => x.id === nid);
                    return n ? n.name : nid;
                });
                html += `<li>Group ${i + 1}: ${names.join(' ↔ ')}</li>`;
            });
            html += '</ul>';
        }
        if (bridges.length > 0) {
            html += '<p><strong>Bridge nodes:</strong></p><ul>';
            bridges.forEach(b => {
                const netNames = (b.nets || []).map(nid => {
                    const n = radioNets.find(x => x.id === nid);
                    return n ? n.name : nid;
                });
                const nodeLabels = (b.bridge_nodes || []).map(nid => {
                    const nd = radioNodes.find(x => x.id === nid);
                    return nd ? nd.label : nid;
                });
                html += `<li>${netNames.join(' ↔ ')}: ${nodeLabels.join(', ')}</li>`;
            });
            html += '</ul>';
        }
        container.innerHTML = html || '<p class="radio-net-help">No connectivity data.</p>';
    } catch (e) {
        container.innerHTML = '<p class="radio-net-help" style="color: #ff4444;">Error loading connectivity.</p>';
    }
}

async function loadRadioNetNonCompliant() {
    const container = document.getElementById('radio-net-non-compliant');
    if (!container) return;
    try {
        const [r, compR] = await Promise.all([
            fetch('/api/radio-nets/non-compliant'),
            fetch('/api/radio-nets/compliance')
        ]);
        const data = await r.json();
        const comp = await compR.json();
        window.radioCompliance = comp;
        const list = data.non_compliant || [];
        if (list.length === 0) {
            container.innerHTML = '<p class="radio-net-help" style="color: var(--accent-green);">All radios are compliant.</p>';
            renderRadioNodeList();
            return;
        }
        container.innerHTML = '<ul style="margin: 0; padding-left: 20px;">' +
            list.map(n => `<li><strong>${escapeHtml(n.label)}</strong>: missing nets ${(n.missing_nets || []).join(', ')}</li>`).join('') +
            '</ul>';
        renderRadioNodeList();
    } catch (e) {
        container.innerHTML = '<p class="radio-net-help" style="color: #ff4444;">Error loading compliance.</p>';
    }
}

function openNetModal(netId = null) {
    const modal = document.getElementById('modal-net');
    const title = document.getElementById('modal-net-title');
    const form = document.getElementById('form-net');
    form.reset();
    document.getElementById('net-id').value = netId || '';
    if (netId) {
        const net = radioNets.find(n => n.id === netId);
        if (net) {
            title.textContent = 'Edit Net';
            document.getElementById('net-name').value = net.name;
            document.getElementById('net-frequency').value = net.frequency_mhz;
            document.getElementById('net-band').value = net.band || 'VHF';
            document.getElementById('net-description').value = net.description || '';
        }
    } else {
        title.textContent = 'Add Net';
    }
    modal.style.display = 'flex';
}

function openNodeModal(nodeId = null) {
    const modal = document.getElementById('modal-node');
    const title = document.getElementById('modal-node-title');
    const form = document.getElementById('form-node');
    form.reset();
    document.getElementById('node-id').value = nodeId || '';
    if (nodeId) {
        const node = radioNodes.find(n => n.id === nodeId);
        if (node) {
            title.textContent = 'Edit Node';
            document.getElementById('node-label').value = node.label;
            document.getElementById('node-configured-nets').value = (node.configured_nets || []).join(', ');
            document.getElementById('node-assigned-nets').value = (node.assigned_nets || []).join(', ');
        }
    } else {
        title.textContent = 'Add Node';
    }
    modal.style.display = 'flex';
}

async function saveNet(e) {
    e.preventDefault();
    const id = document.getElementById('net-id').value;
    const body = {
        name: document.getElementById('net-name').value.trim(),
        frequency_mhz: parseFloat(document.getElementById('net-frequency').value),
        band: document.getElementById('net-band').value,
        description: document.getElementById('net-description').value.trim()
    };
    try {
        if (id) {
            await fetch(`/api/radio-nets/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        } else {
            await fetch('/api/radio-nets', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        }
        document.getElementById('modal-net').style.display = 'none';
        await loadRadioNets();
    } catch (err) {
        console.error('Error saving net:', err);
    }
}

async function saveNode(e) {
    e.preventDefault();
    const id = document.getElementById('node-id').value;
    const configured = document.getElementById('node-configured-nets').value.split(',').map(s => s.trim()).filter(Boolean);
    const assigned = document.getElementById('node-assigned-nets').value.split(',').map(s => s.trim()).filter(Boolean);
    const body = {
        label: document.getElementById('node-label').value.trim(),
        configured_nets: configured,
        assigned_nets: assigned
    };
    try {
        if (id) {
            await fetch(`/api/radio-nodes/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        } else {
            await fetch('/api/radio-nodes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        }
        document.getElementById('modal-node').style.display = 'none';
        await loadRadioNodes();
    } catch (err) {
        console.error('Error saving node:', err);
    }
}

async function deleteNet(netId) {
    if (!confirm('Delete this net? It will be removed from all nodes.')) return;
    try {
        await fetch(`/api/radio-nets/${netId}`, { method: 'DELETE' });
        await loadRadioNets();
        await loadRadioNodes();
    } catch (err) {
        console.error('Error deleting net:', err);
    }
}

async function deleteNode(nodeId) {
    if (!confirm('Delete this node?')) return;
    try {
        await fetch(`/api/radio-nodes/${nodeId}`, { method: 'DELETE' });
        await loadRadioNodes();
    } catch (err) {
        console.error('Error deleting node:', err);
    }
}

function setupRadioNetUI() {
    const btnAddNet = document.getElementById('btn-add-net');
    const btnAddNode = document.getElementById('btn-add-node');
    const btnCancelNet = document.getElementById('btn-cancel-net');
    const btnCancelNode = document.getElementById('btn-cancel-node');
    const formNet = document.getElementById('form-net');
    const formNode = document.getElementById('form-node');
    if (btnAddNet) btnAddNet.addEventListener('click', () => openNetModal());
    if (btnAddNode) btnAddNode.addEventListener('click', () => openNodeModal());
    if (btnCancelNet) btnCancelNet.addEventListener('click', () => { document.getElementById('modal-net').style.display = 'none'; });
    if (btnCancelNode) btnCancelNode.addEventListener('click', () => { document.getElementById('modal-node').style.display = 'none'; });
    if (formNet) formNet.addEventListener('submit', saveNet);
    if (formNode) formNode.addEventListener('submit', saveNode);
}

// Satellite Communications state and functions
let satellites = [];
let plannedUsageList = [];

async function loadSatellites() {
    try {
        const r = await fetch('/api/satellites');
        const data = await r.json();
        satellites = data.satellites || [];
        renderSatelliteList();
        updateSatelliteFootprints();
    } catch (e) {
        console.error('Error loading satellites:', e);
    }
}

async function loadPlannedUsage() {
    try {
        const r = await fetch('/api/satellites/planned-usage');
        const data = await r.json();
        plannedUsageList = data.planned_usage || [];
        renderPlannedUsageList();
    } catch (e) {
        console.error('Error loading planned usage:', e);
    }
}

async function loadNodesPerSatellite() {
    const threshold = parseInt(document.getElementById('saturation-threshold')?.value || '10', 10);
    try {
        const r = await fetch(`/api/satellites/nodes-per-satellite?saturation_threshold=${threshold}`);
        const data = await r.json();
        renderNodesPerSatellite(data);
        renderSaturatedSatellites(data);
        updateSatelliteFootprints(data);
    } catch (e) {
        console.error('Error loading nodes per satellite:', e);
    }
}

function renderSatelliteList() {
    const container = document.getElementById('satellite-list');
    if (!container) return;
    container.innerHTML = '';
    satellites.forEach(sat => {
        const div = document.createElement('div');
        div.className = 'radio-net-item';
        div.innerHTML = `
            <div>
                <strong>${escapeHtml(sat.name)}</strong>
                <span style="font-size: 11px; color: var(--text-secondary); display: block;">
                    ${sat.footprint_center_lat?.toFixed(2)}, ${sat.footprint_center_lon?.toFixed(2)} | r=${sat.footprint_radius_km} km
                </span>
            </div>
            <div class="item-actions">
                <button type="button" class="btn btn-secondary btn-edit-satellite" data-id="${sat.id}">Edit</button>
                <button type="button" class="btn btn-danger btn-delete-satellite" data-id="${sat.id}">Delete</button>
            </div>
        `;
        div.querySelector('.btn-edit-satellite').addEventListener('click', () => openSatelliteModal(sat.id));
        div.querySelector('.btn-delete-satellite').addEventListener('click', () => deleteSatellite(sat.id));
        container.appendChild(div);
    });
}

function renderPlannedUsageList() {
    const container = document.getElementById('planned-usage-list');
    if (!container) return;
    container.innerHTML = '';
    const nodeLabels = {};
    radioNodes.forEach(n => { nodeLabels[n.id] = n.label; });
    const satNames = {};
    satellites.forEach(s => { satNames[s.id] = s.name; });
    plannedUsageList.slice(0, 30).forEach(u => {
        const div = document.createElement('div');
        div.className = 'radio-net-item';
        div.innerHTML = `
            <div style="font-size: 12px;">
                ${escapeHtml(nodeLabels[u.node_id] || u.node_id)} → ${escapeHtml(satNames[u.satellite_id] || u.satellite_id)}
                <span style="color: var(--text-secondary); display: block; font-size: 11px;">
                    ${u.start_time || ''} – ${u.end_time || ''}
                </span>
            </div>
            <div class="item-actions">
                <button type="button" class="btn btn-danger btn-delete-usage" data-id="${u.id}">Delete</button>
            </div>
        `;
        div.querySelector('.btn-delete-usage').addEventListener('click', () => deleteUsage(u.id));
        container.appendChild(div);
    });
    if (plannedUsageList.length > 30) {
        const more = document.createElement('div');
        more.className = 'radio-net-help';
        more.style.marginTop = '8px';
        more.textContent = `+ ${plannedUsageList.length - 30} more`;
        container.appendChild(more);
    }
}

function renderNodesPerSatellite(data) {
    const container = document.getElementById('nodes-per-satellite');
    if (!container) return;
    const sats = data?.satellites || [];
    if (sats.length === 0) {
        container.innerHTML = '<p class="radio-net-help">No satellites or no usage data.</p>';
        return;
    }
    container.innerHTML = '<ul style="margin: 0; padding-left: 20px;">' +
        sats.map(s => `<li>${escapeHtml(s.name)}: <strong>${s.node_count}</strong> nodes${s.saturated ? ' ⚠ saturated' : ''}</li>`).join('') +
        '</ul>';
}

function renderSaturatedSatellites(data) {
    const container = document.getElementById('saturated-satellites');
    if (!container) return;
    const saturated = (data?.satellites || []).filter(s => s.saturated);
    if (saturated.length === 0) {
        container.innerHTML = '<p class="radio-net-help" style="color: var(--accent-green);">None.</p>';
        return;
    }
    container.innerHTML = '<ul style="margin: 0; padding-left: 20px; color: #ff4444;">' +
        saturated.map(s => `<li>${escapeHtml(s.name)}: ${s.node_count} nodes (threshold ${data?.saturation_threshold || 10})</li>`).join('') +
        '</ul>';
}

async function updateSatelliteFootprints(nodesPerSatData) {
    if (!map || !satelliteFootprintLayer) return;
    if (!satelliteFootprintsEnabled) {
        map.removeLayer(satelliteFootprintLayer);
        satelliteFootprintLayer.clearLayers();
        return;
    }
    const footprints = satellites.length ? satellites : (await fetch('/api/satellites/footprints').then(r => r.json()).then(d => d.footprints || []));
    satelliteFootprintLayer.clearLayers();
    const satBySaturated = (nodesPerSatData?.satellites || []).reduce((acc, s) => { acc[s.id] = s.saturated; return acc; }, {});
    footprints.forEach(sat => {
        const radiusM = (sat.footprint_radius_km || 0) * 1000;
        const saturated = satBySaturated[sat.id];
        const circle = L.circle([sat.footprint_center_lat, sat.footprint_center_lon], {
            radius: radiusM,
            color: saturated ? '#ff4444' : '#00aaff',
            fillColor: saturated ? '#ff4444' : '#00aaff',
            fillOpacity: 0.15,
            weight: 2
        });
        circle.bindPopup(`<strong>${escapeHtml(sat.name)}</strong><br/>Radius: ${sat.footprint_radius_km} km`);
        circle.addTo(satelliteFootprintLayer);
    });
    map.addLayer(satelliteFootprintLayer);
}

function openSatelliteModal(satId = null) {
    const modal = document.getElementById('modal-satellite');
    const title = document.getElementById('modal-satellite-title');
    const form = document.getElementById('form-satellite');
    form.reset();
    document.getElementById('satellite-id').value = satId || '';
    if (satId) {
        const sat = satellites.find(s => s.id === satId);
        if (sat) {
            title.textContent = 'Edit Satellite';
            document.getElementById('satellite-name').value = sat.name;
            document.getElementById('satellite-lat').value = sat.footprint_center_lat;
            document.getElementById('satellite-lon').value = sat.footprint_center_lon;
            document.getElementById('satellite-radius').value = sat.footprint_radius_km;
        }
    } else {
        title.textContent = 'Add Satellite';
    }
    modal.style.display = 'flex';
}

function openUsageModal() {
    const modal = document.getElementById('modal-usage');
    const sel = document.getElementById('usage-satellite-id');
    sel.innerHTML = satellites.map(s => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join('');
    const now = new Date();
    const pad = n => String(n).padStart(2, '0');
    document.getElementById('usage-start-time').value = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
    document.getElementById('usage-end-time').value = document.getElementById('usage-start-time').value;
    modal.style.display = 'flex';
}

async function saveSatellite(e) {
    e.preventDefault();
    const id = document.getElementById('satellite-id').value;
    const body = {
        name: document.getElementById('satellite-name').value.trim(),
        footprint_center_lat: parseFloat(document.getElementById('satellite-lat').value),
        footprint_center_lon: parseFloat(document.getElementById('satellite-lon').value),
        footprint_radius_km: parseFloat(document.getElementById('satellite-radius').value)
    };
    try {
        if (id) {
            await fetch(`/api/satellites/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        } else {
            await fetch('/api/satellites', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        }
        document.getElementById('modal-satellite').style.display = 'none';
        await loadSatellites();
    } catch (err) {
        console.error('Error saving satellite:', err);
    }
}

async function saveUsage(e) {
    e.preventDefault();
    const nodeId = document.getElementById('usage-node-id').value.trim();
    const satelliteId = document.getElementById('usage-satellite-id').value;
    const startLocal = document.getElementById('usage-start-time').value;
    const endLocal = document.getElementById('usage-end-time').value;
    const startTime = startLocal ? new Date(startLocal).toISOString() : '';
    const endTime = endLocal ? new Date(endLocal).toISOString() : '';
    try {
        await fetch('/api/satellites/planned-usage', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node_id: nodeId, satellite_id: satelliteId, start_time: startTime, end_time: endTime })
        });
        document.getElementById('modal-usage').style.display = 'none';
        await loadPlannedUsage();
        await loadNodesPerSatellite();
    } catch (err) {
        console.error('Error saving usage:', err);
    }
}

async function deleteSatellite(satId) {
    if (!confirm('Delete this satellite? All planned usage for it will be removed.')) return;
    try {
        await fetch(`/api/satellites/${satId}`, { method: 'DELETE' });
        await loadSatellites();
        await loadPlannedUsage();
        await loadNodesPerSatellite();
    } catch (err) {
        console.error('Error deleting satellite:', err);
    }
}

async function deleteUsage(usageId) {
    try {
        await fetch(`/api/satellites/planned-usage/${usageId}`, { method: 'DELETE' });
        await loadPlannedUsage();
        await loadNodesPerSatellite();
    } catch (err) {
        console.error('Error deleting usage:', err);
    }
}

function setupSatelliteUI() {
    const btnAddSat = document.getElementById('btn-add-satellite');
    const btnAddUsage = document.getElementById('btn-add-usage');
    const btnCancelSat = document.getElementById('btn-cancel-satellite');
    const btnCancelUsage = document.getElementById('btn-cancel-usage');
    const btnRefresh = document.getElementById('btn-refresh-sat-stats');
    const formSat = document.getElementById('form-satellite');
    const formUsage = document.getElementById('form-usage');
    const toggle = document.getElementById('satellite-footprints-toggle');
    if (btnAddSat) btnAddSat.addEventListener('click', () => openSatelliteModal());
    if (btnAddUsage) btnAddUsage.addEventListener('click', () => openUsageModal());
    if (btnCancelSat) btnCancelSat.addEventListener('click', () => { document.getElementById('modal-satellite').style.display = 'none'; });
    if (btnCancelUsage) btnCancelUsage.addEventListener('click', () => { document.getElementById('modal-usage').style.display = 'none'; });
    if (formSat) formSat.addEventListener('submit', saveSatellite);
    if (formUsage) formUsage.addEventListener('submit', saveUsage);
    if (btnRefresh) btnRefresh.addEventListener('click', () => loadNodesPerSatellite());
    if (toggle) {
        toggle.addEventListener('change', (e) => {
            satelliteFootprintsEnabled = e.target.checked;
            updateSatelliteFootprints();
            if (satelliteFootprintsEnabled) loadNodesPerSatellite();
        });
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    debugLog('main.js:42', 'DOMContentLoaded', {
        hasPlotly: typeof Plotly !== 'undefined',
        hasLeaflet: typeof L !== 'undefined',
        hasD3: typeof d3 !== 'undefined'
    });
    
    try {
        await loadCarriers();
        setupConfiguration();
        setupAirportToggle();
        setupExpandableSections();
        setupRadioNetUI();
        setupSatelliteUI();
        initializePlotlyCharts();
        initializeGraph();
        initializeLeafletMap();
        loadRadioNets();
        loadRadioNodes();
        loadSatellites();
        loadPlannedUsage();
        loadNodesPerSatellite();
        
        // Verify we have a default carrier selected before refreshing
        if (selectedCarriers.size > 0) {
            updateLOSStatus('Waiting for aircraft data...', 'calculating');
            // Wait for aircraft data to be available before calculating LOS
            let aircraftAvailable = false;
            let attempts = 0;
            const maxAttempts = 10;
            while (!aircraftAvailable && attempts < maxAttempts) {
                try {
                    const aircraftResp = await fetch('/api/aircraft');
                    const aircraftData = await aircraftResp.json();
                    const aircraftCount = aircraftData?.aircraft?.length || 0;
                    if (aircraftCount > 0) {
                        aircraftAvailable = true;
                    } else {
                        attempts++;
                        await new Promise(resolve => setTimeout(resolve, 500)); // Wait 500ms before retry
                    }
                } catch (error) {
                    attempts++;
                    await new Promise(resolve => setTimeout(resolve, 500));
                }
            }
            
            if (aircraftAvailable) {
                updateLOSStatus('Calculating LOS distances...', 'calculating');
                debugLog('main.js:DOMContentLoaded', 'Triggering initial refreshData', {
                    selectedCarriers: Array.from(selectedCarriers),
                    includeAirports,
                    carrierRanges: Object.keys(carrierRanges).length
                });
                await refreshData();
            } else {
                updateLOSStatus('Aircraft data not available', 'waiting');
            }
        } else {
            updateLOSStatus('Waiting for carrier selection', 'waiting');
        }
        
        startAutoRefresh();
        // Check LOS Calculation status on load and then every 30 seconds
        checkLOSAPIStatus();
        setInterval(checkLOSAPIStatus, 30000); // Check every 30 seconds
        debugLog('main.js:56', 'DOMContentLoaded success');
    } catch (e) {
        debugLog('main.js:58', 'DOMContentLoaded error', {
            error: e.message,
            stack: e.stack
        });
        console.error('Initialization error:', e);
        updateLOSStatus('Initialization error', 'error');
    }
});

// Load available carriers from API
async function loadCarriers() {
    try {
        const response = await fetch('/api/carriers');
        carriers = await response.json();
        
        // Initialize carrier ranges first (before rendering)
        initializeCarrierRanges();
        
        // Set default carrier (AAL only)
        const defaultCarrier = 'AAL'; // American Airlines
        if (carriers[defaultCarrier]) {
            selectedCarriers.add(defaultCarrier);
        }
        
        // Render carrier list (this will set checkbox states based on selectedCarriers)
        renderCarrierList();
        
        // Set airport toggle to checked
        const airportToggle = document.getElementById('include-airports-toggle');
        if (airportToggle) {
            airportToggle.checked = includeAirports;
        }
        
        // Verify default selection is ready
        debugLog('main.js:loadCarriers', 'Default carrier setup', {
            defaultCarrier,
            isSelected: selectedCarriers.has(defaultCarrier),
            selectedCarriersSize: selectedCarriers.size,
            hasRange: !!carrierRanges[defaultCarrier],
            includeAirports
        });
    } catch (error) {
        console.error('Error loading carriers:', error);
        updateStatus('Error loading carriers', 'error');
    }
}

// Render carrier selection boxes
function renderCarrierList() {
    const container = document.getElementById('carrier-list');
    container.innerHTML = '';
    
    // Sort carriers by name for better UX
    const sortedCarriers = Object.entries(carriers).sort((a, b) => 
        a[1].name.localeCompare(b[1].name)
    );
    
    for (const [code, info] of sortedCarriers) {
        const carrierBox = document.createElement('div');
        carrierBox.className = 'carrier-box';
        carrierBox.innerHTML = `
            <div class="carrier-box-header">
                <input type="checkbox" id="carrier-${code}" value="${code}" class="carrier-checkbox-input">
                <label for="carrier-${code}" class="carrier-box-label">
                    <span class="carrier-name">${info.name}</span>
                    <span class="carrier-code">(${code})</span>
                </label>
            </div>
            <div class="carrier-box-range">
                <label for="range-${code}" class="range-label">Range (km):</label>
                <input 
                    type="number" 
                    id="range-${code}" 
                    class="range-input"
                    value="${carrierRanges[code] || info.default_range_km}" 
                    min="50" 
                    max="500" 
                    step="10"
                    disabled
                >
            </div>
        `;
        
        // Handle checkbox change
        const checkbox = carrierBox.querySelector('.carrier-checkbox-input');
        checkbox.addEventListener('change', (e) => {
            const carrier = e.target.value;
            const rangeInput = carrierBox.querySelector('.range-input');
            
            if (e.target.checked) {
                selectedCarriers.add(carrier);
                rangeInput.disabled = false;
            } else {
                selectedCarriers.delete(carrier);
                rangeInput.disabled = true;
            }
            updateSelectedCarriersBadge();
            refreshData();
        });
        
        // Handle range input change
        const rangeInput = carrierBox.querySelector('.range-input');
        rangeInput.addEventListener('change', (e) => {
            carrierRanges[code] = parseFloat(e.target.value);
            refreshData();
        });
        
        // Initialize checkbox state
        if (selectedCarriers.has(code)) {
            checkbox.checked = true;
            rangeInput.disabled = false;
        } else {
            checkbox.checked = false;
            rangeInput.disabled = true;
        }
        
        container.appendChild(carrierBox);
    }
    
    // Update badge after rendering
    updateSelectedCarriersBadge();
}

// Update selected carriers badge in header
function updateSelectedCarriersBadge() {
    const badge = document.getElementById('selected-carriers-badge');
    if (!badge) return;
    
    if (selectedCarriers.size === 0) {
        badge.textContent = '';
        badge.style.display = 'none';
    } else {
        const allSelected = Array.from(selectedCarriers).sort();
        badge.textContent = `(${allSelected.join(', ')})`;
        badge.style.display = 'inline';
    }
}

// Setup configuration panel (no longer needed, handled inline in carrier boxes)
function setupConfiguration() {
    // Configuration is now handled inline in carrier boxes
}

// Initialize carrier ranges with defaults
function initializeCarrierRanges() {
    for (const [code, info] of Object.entries(carriers)) {
        carrierRanges[code] = info.default_range_km;
    }
}

// Setup airport toggle handler
function setupAirportToggle() {
    const toggle = document.getElementById('include-airports-toggle');
    if (toggle) {
        toggle.addEventListener('change', (e) => {
            includeAirports = e.target.checked;
            refreshData();
        });
    }
}

// Setup expandable sections
function setupExpandableSections() {
    const header = document.getElementById('carrier-selection-header');
    const content = document.getElementById('carrier-selection-content');
    
    if (header && content) {
        // Start expanded by default
        content.style.display = 'block';
        header.classList.add('expanded');
        
        header.addEventListener('click', () => {
            const isExpanded = header.classList.contains('expanded');
            
            if (isExpanded) {
                // Collapse
                content.style.display = 'none';
                header.classList.remove('expanded');
            } else {
                // Expand
                content.style.display = 'block';
                header.classList.add('expanded');
            }
        });
        
        // Make header cursor pointer
        header.style.cursor = 'pointer';
    }
}

// Initialize Plotly.js charts
function initializePlotlyCharts() {
    debugLog('main.js:158', 'initializePlotlyCharts entry', {
        hasPlotly: typeof Plotly !== 'undefined',
        hasConnectionChart: !!document.getElementById('connection-chart')
    });
    
    // Connection distribution chart
    const connectionData = [{
        x: [],
        y: [],
        type: 'bar',
        marker: {
            color: 'rgba(0, 255, 136, 0.3)',
            line: {
                color: 'rgba(0, 255, 136, 0.8)',
                width: 1
            }
        }
    }];
    
    const connectionLayout = {
        plot_bgcolor: 'rgba(0, 0, 0, 0)',
        paper_bgcolor: 'rgba(0, 0, 0, 0)',
        font: {
            color: '#b0b0b0'
        },
        xaxis: {
            title: 'Number of Connections',
            gridcolor: 'rgba(255, 255, 255, 0.05)',
            showgrid: true
        },
        yaxis: {
            title: 'Number of Aircraft',
            gridcolor: 'rgba(255, 255, 255, 0.05)',
            showgrid: true,
            zeroline: true
        },
        margin: { l: 50, r: 20, t: 20, b: 50 },
        autosize: true
    };
    
    const connectionConfig = {
        responsive: true,
        displayModeBar: false
    };
    
    try {
        Plotly.newPlot('connection-chart', connectionData, connectionLayout, connectionConfig);
        debugLog('main.js:239', 'Plotly.newPlot connection-chart success');
    } catch (e) {
        debugLog('main.js:241', 'Plotly.newPlot connection-chart error', { error: e.message });
        throw e;
    }
    
    // Connectivity curve chart (cumulative pairs)
    const connectivityCurveData = [{
        x: ['Direct', '1-Hop', '2-Hop', '3-Hop', '4-Hop', '5-Hop'],
        y: [0, 0, 0, 0, 0, 0],
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Cumulative Pairs',
        line: {
            color: '#00ff88',
            width: 3
        },
        marker: {
            color: '#00ff88',
            size: 8
        }
    }];
    
    const connectivityCurveLayout = {
        plot_bgcolor: 'rgba(0, 0, 0, 0)',
        paper_bgcolor: 'rgba(0, 0, 0, 0)',
        font: { color: '#a0b0b2' },
        title: {
            text: 'Cumulative Connectivity (Pairs Reachable)',
            font: { size: 14, color: '#a0b0b2' }
        },
        xaxis: {
            title: 'Hop Count',
            gridcolor: '#2a3536',
            showgrid: true
        },
        yaxis: {
            title: 'Number of Pairs',
            gridcolor: '#2a3536',
            showgrid: true,
            zeroline: true
        },
        margin: { l: 60, r: 20, t: 50, b: 50 },
        autosize: true
    };
    
    const connectivityCurveConfig = {
        responsive: true,
        displayModeBar: false
    };
    
    try {
        Plotly.newPlot('connectivity-curve-chart', connectivityCurveData, connectivityCurveLayout, connectivityCurveConfig);
    } catch (e) {
        debugLog('main.js:connectivity-curve-init', 'Plotly.newPlot connectivity-curve-chart error', { error: e.message });
    }
    
    // Marginal improvement chart
    const marginalData = [{
        x: ['1-Hop', '2-Hop', '3-Hop', '4-Hop', '5-Hop'],
        y: [0, 0, 0, 0, 0],
        type: 'bar',
        name: 'Marginal Improvement',
        marker: {
            color: 'rgba(255, 136, 0, 0.6)',
            line: {
                color: '#ff8800',
                width: 1
            }
        }
    }];
    
    const marginalLayout = {
        plot_bgcolor: 'rgba(0, 0, 0, 0)',
        paper_bgcolor: 'rgba(0, 0, 0, 0)',
        font: { color: '#a0b0b2' },
        title: {
            text: 'Marginal Improvement per Hop (Knee Detection)',
            font: { size: 14, color: '#a0b0b2' }
        },
        xaxis: {
            title: 'Hop Count',
            gridcolor: '#2a3536',
            showgrid: true
        },
        yaxis: {
            title: 'Additional Pairs',
            gridcolor: '#2a3536',
            showgrid: true,
            zeroline: true
        },
        margin: { l: 60, r: 20, t: 50, b: 50 },
        autosize: true
    };
    
    const marginalConfig = {
        responsive: true,
        displayModeBar: false
    };
    
    try {
        Plotly.newPlot('marginal-improvement-chart', marginalData, marginalLayout, marginalConfig);
    } catch (e) {
        debugLog('main.js:marginal-init', 'Plotly.newPlot marginal-improvement-chart error', { error: e.message });
    }
    
    
    // Range sensitivity chart
    const rangeSensitivityData = [
        {
            x: [],
            y: [],
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Direct Connections',
            line: {
                color: '#00ff88',
                width: 2
            },
            marker: {
                color: '#00ff88',
                size: 6
            }
        },
        {
            x: [],
            y: [],
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Total Reachable Pairs',
            line: {
                color: '#00aaff',
                width: 2
            },
            marker: {
                color: '#00aaff',
                size: 6
            }
        },
        {
            x: [],
            y: [],
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Graph Density',
            yaxis: 'y2',
            line: {
                color: '#ff8800',
                width: 2
            },
            marker: {
                color: '#ff8800',
                size: 6
            }
        }
    ];
    
    const rangeSensitivityLayout = {
        plot_bgcolor: 'rgba(0, 0, 0, 0)',
        paper_bgcolor: 'rgba(0, 0, 0, 0)',
        font: { color: '#a0b0b2' },
        title: {
            text: 'Connectivity vs Communication Range',
            font: { size: 16, color: '#a0b0b2' }
        },
        xaxis: {
            title: 'Communication Range (km)',
            gridcolor: '#2a3536',
            showgrid: true
        },
        yaxis: {
            title: 'Number of Connections/Pairs',
            gridcolor: '#2a3536',
            showgrid: true,
            zeroline: true,
            side: 'left'
        },
        yaxis2: {
            title: 'Graph Density',
            gridcolor: '#2a3536',
            showgrid: false,
            zeroline: false,
            overlaying: 'y',
            side: 'right'
        },
        legend: {
            x: 0.02,
            y: 0.98,
            bgcolor: 'rgba(0, 0, 0, 0.5)',
            bordercolor: '#2a3536',
            borderwidth: 1
        },
        margin: { l: 60, r: 60, t: 60, b: 50 },
        autosize: true
    };
    
    const rangeSensitivityConfig = {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['pan2d', 'lasso2d']
    };
    
    try {
        Plotly.newPlot('range-sensitivity-chart', rangeSensitivityData, rangeSensitivityLayout, rangeSensitivityConfig);
    } catch (e) {
        debugLog('main.js:range-sensitivity-init', 'Plotly.newPlot range-sensitivity-chart error', { error: e.message });
    }
}

// Refresh all data
async function refreshData() {
    debugLog('main.js:229', 'refreshData entry', { selectedCarriersSize: selectedCarriers.size });
    
    if (selectedCarriers.size === 0) {
        updateStats({ direct: 0, '1hop': 0, '2hop': 0, '3hop': 0 });
        updateConnectionChart(null);
        updateLeafletMap([], { nodes: [], edges: [] });
        updateLOSMetrics(null);
        updateConnectivityCurve(null);
        updateRangeSensitivity(null);
        updateLOSStatus('Waiting for carrier selection', 'waiting');
        return;
    }
    
    updateStatus('Refreshing...', 'loading');
    updateLOSStatus('Calculating LOS distances...', 'calculating');
    
    try {
        const carriersArray = Array.from(selectedCarriers);
        const rangesObj = {};
        carriersArray.forEach(code => {
            rangesObj[code] = carrierRanges[code] || carriers[code].default_range_km;
        });
        
        debugLog('main.js:247', 'Before API calls', { carriersArray, rangesObj });
        
        // Get airport toggle state
        const includeAirportsFlag = includeAirports;
        
        // Build request body
        const requestBody = {
            carriers: carriersArray,
            carrier_ranges: rangesObj,
            include_airports: includeAirportsFlag
        };
        
        // Fetch all data in parallel
        const [distancesResp, commResp, graphResp, metricsResp, curveResp, rangeSensitivityResp] = await Promise.all([
            fetch('/api/distances', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            }),
            fetch('/api/communication', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            }),
            fetch('/api/graph', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            }),
            fetch('/api/los-metrics', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    carriers: carriersArray,
                    carrier_ranges: rangesObj
                })
            }),
            fetch('/api/connectivity-curve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    carriers: carriersArray,
                    carrier_ranges: rangesObj
                })
            }),
            fetch('/api/range-sensitivity', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    carriers: carriersArray,
                    carrier_ranges: rangesObj
                })
            })
        ]);
        
        debugLog('main.js:283', 'API responses received', {
            distancesStatus: distancesResp.status,
            commStatus: commResp.status,
            graphStatus: graphResp.status,
            metricsStatus: metricsResp.status,
            curveStatus: curveResp.status,
            distancesOk: distancesResp.ok,
            commOk: commResp.ok,
            graphOk: graphResp.ok,
            metricsOk: metricsResp.ok,
            curveOk: curveResp.ok
        });
        
        const distancesData = await distancesResp.json();
        const commData = await commResp.json();
            const graphData = await graphResp.json();
            lastGraphData = graphData; // Store for status checks
        const metricsData = await metricsResp.json();
        const curveData = await curveResp.json();
        const rangeSensitivityData = await rangeSensitivityResp.json();
        
        debugLog('main.js:289', 'JSON parsed', {
            hasDistancesData: !!distancesData,
            hasCommData: !!commData,
            hasGraphData: !!graphData,
            hasMetricsData: !!metricsData,
            hasCurveData: !!curveData,
            hasRangeSensitivityData: !!rangeSensitivityData,
            graphNodesCount: graphData?.nodes?.length || 0,
            graphEdgesCount: graphData?.edges?.length || 0,
            graphHasEdges: !!(graphData?.edges && graphData.edges.length > 0)
        });
        
        if (distancesResp.ok && commResp.ok && graphResp.ok && metricsResp.ok && curveResp.ok && rangeSensitivityResp.ok) {
            // Update chart
            // Update statistics
            updateStats(commData);
            
            // Update graphs (pass graphData to avoid duplicate API call)
            await updateGraph(graphData);
            
            // Update connection distribution chart
            updateConnectionChart(graphData);
            
            // Update Leaflet map (use the same graphData)
            const aircraftList = await fetch('/api/aircraft').then(r => r.json()).then(d => d.aircraft || []);
            const filteredAircraft = aircraftList.filter(a => carriersArray.includes(a.carrier_code));
            await updateLeafletMap(filteredAircraft, graphData);
            
            // Update LOS metrics
            updateLOSMetrics(metricsData);
            
            // Update connectivity curve charts
            updateConnectivityCurve(curveData);
            
            // Update range sensitivity chart
            updateRangeSensitivity(rangeSensitivityData);
            
            // Update LOS status
            const losPairs = metricsData.coverage?.los_pairs_count || 0;
            const totalPairs = metricsData.coverage?.total_pairs || 0;
            const hasEdges = graphData?.edges && graphData.edges.length > 0;
            
            if (hasEdges && losPairs > 0) {
                updateLOSStatus(`Complete: ${losPairs} LOS pairs of ${totalPairs} total`, 'complete');
            } else if (distancesData.aircraft_count > 0) {
                updateLOSStatus('No LOS connections found', 'waiting');
            } else {
                updateLOSStatus('No aircraft selected', 'waiting');
            }
            
            // Update LOS Calculation status after data refresh
            checkLOSAPIStatus();
            
            // Update status
            const lastUpdate = distancesData.last_update 
                ? new Date(distancesData.last_update).toLocaleTimeString()
                : 'Unknown';
            updateStatus(`Last updated: ${lastUpdate} | ${distancesData.aircraft_count} aircraft`, 'success');
            debugLog('main.js:323', 'refreshData success');
        } else {
            debugLog('main.js:325', 'API error - not all OK', {
                distancesOk: distancesResp.ok,
                commOk: commResp.ok,
                graphOk: graphResp.ok,
                metricsOk: metricsResp.ok,
                curveOk: curveResp.ok,
                rangeSensitivityOk: rangeSensitivityResp.ok
            });
            updateLOSStatus('Error: API request failed', 'error');
            throw new Error('API error');
        }
        
    } catch (error) {
        debugLog('main.js:334', 'refreshData catch block', {
            errorMessage: error.message,
            errorStack: error.stack,
            errorName: error.name
        });
        console.error('Error refreshing data:', error);
        updateStatus('Error loading data', 'error');
        updateLOSStatus('Error calculating LOS', 'error');
    }
}

// Update distance chart data
// Calculate and update connection distribution chart
function updateConnectionChart(graphData) {
    if (!graphData || !graphData.nodes || !graphData.edges) {
        // Clear chart
        Plotly.restyle('connection-chart', { x: [[]], y: [[]] });
        return;
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
        Plotly.restyle('connection-chart', { x: [[]], y: [[]] });
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
    Plotly.restyle('connection-chart', { x: [labels], y: [data] });
}

// Update connectivity curve charts
function updateConnectivityCurve(curveData) {
    if (!curveData || !curveData.cumulative_pairs || !curveData.marginal_improvement) {
        Plotly.restyle('connectivity-curve-chart', { y: [[0, 0, 0, 0, 0, 0]] });
        Plotly.restyle('marginal-improvement-chart', { y: [[0, 0, 0, 0, 0]] });
        return;
    }
    
    const cumulative = curveData.cumulative_pairs;
    const cumulativeValues = [
        cumulative.direct || 0,
        cumulative['1hop'] || 0,
        cumulative['2hop'] || 0,
        cumulative['3hop'] || 0,
        cumulative['4hop'] || 0,
        cumulative['5hop'] || 0
    ];
    
    const marginal = curveData.marginal_improvement;
    const marginalValues = [
        marginal['1hop'] || 0,
        marginal['2hop'] || 0,
        marginal['3hop'] || 0,
        marginal['4hop'] || 0,
        marginal['5hop'] || 0
    ];
    
    // Update cumulative chart
    Plotly.restyle('connectivity-curve-chart', { y: [cumulativeValues] });
    
    // Update marginal improvement chart
    Plotly.restyle('marginal-improvement-chart', { y: [marginalValues] });
    
    // Add annotation for knee if detected
    if (curveData.knee_hop) {
        const kneeIndex = ['1hop', '2hop', '3hop', '4hop', '5hop'].indexOf(curveData.knee_hop);
        if (kneeIndex >= 0) {
            const annotations = [{
                x: kneeIndex + 1, // +1 because x-axis starts at '1-Hop'
                y: marginalValues[kneeIndex],
                text: 'Knee',
                showarrow: true,
                arrowhead: 2,
                arrowcolor: '#ff8800',
                font: { color: '#ff8800', size: 12 }
            }];
            
            Plotly.relayout('marginal-improvement-chart', { annotations: annotations });
        }
    }
}


// Update range sensitivity chart
function updateRangeSensitivity(sensitivityData) {
    if (!sensitivityData || !sensitivityData.sensitivity_data || sensitivityData.sensitivity_data.length === 0) {
        Plotly.restyle('range-sensitivity-chart', {
            x: [[], [], []],
            y: [[], [], []]
        });
        return;
    }
    
    const data = sensitivityData.sensitivity_data;
    const ranges = data.map(d => d.range_km);
    const directConnections = data.map(d => d.direct_connections || 0);
    const totalReachablePairs = data.map(d => d.total_reachable_pairs || 0);
    const graphDensity = data.map(d => d.graph_density || 0);
    
    // Update all three traces
    Plotly.restyle('range-sensitivity-chart', {
        x: [ranges, ranges, ranges],
        y: [directConnections, totalReachablePairs, graphDensity]
    }, [0, 1, 2]);
    
    // Add vertical lines for current carrier ranges if available
    if (sensitivityData.current_ranges && Object.keys(sensitivityData.current_ranges).length > 0) {
        const currentRanges = Object.values(sensitivityData.current_ranges);
        const uniqueRanges = [...new Set(currentRanges)];
        
        // Add shapes (vertical lines) for current ranges
        const shapes = uniqueRanges.map(range => ({
            type: 'line',
            x0: range,
            x1: range,
            y0: 0,
            y1: 1,
            yref: 'paper',
            line: {
                color: '#ff00ff',
                width: 2,
                dash: 'dash'
            }
        }));
        
        Plotly.relayout('range-sensitivity-chart', { shapes: shapes });
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

// Update LOS calculations status indicator
function updateLOSStatus(text, type = 'waiting') {
    const losStatus = document.getElementById('los-status');
    const losStatusText = document.getElementById('los-status-text');
    
    if (!losStatus || !losStatusText) {
        return; // Element might not exist yet
    }
    
    losStatusText.textContent = text;
    
    // Remove all status classes
    losStatus.classList.remove('calculating', 'complete', 'error', 'waiting');
    
    // Add the appropriate class
    losStatus.classList.add(type);
}

// Check LOS Calculation data availability status
async function checkLOSAPIStatus() {
    try {
        const response = await fetch('/api/los-status');
        if (!response.ok) {
            updateLOSAPIStatus('Unavailable', 'error');
            return;
        }
        
        const data = await response.json();
        const statusText = document.getElementById('los-api-status-text');
        const statusIcon = document.getElementById('los-api-status-icon');
        
        if (!statusText || !statusIcon) {
            return;
        }
        
        // Check if we have carriers selected
        const hasSelectedCarriers = selectedCarriers.size > 0;
        
        // Check if we have actual LOS calculations
        // Check stored graphData first (most reliable)
        let hasGraphEdges = false;
        if (lastGraphData && lastGraphData.edges && lastGraphData.edges.length > 0) {
            hasGraphEdges = true;
        } else if (graphSvg) {
            // Fallback: check rendered edges in SVG
            const edgeCount = graphSvg.selectAll('.graph-edge').size();
            hasGraphEdges = edgeCount > 0;
        }
        
        // Check if metrics show actual data (not all zeros)
        const directStat = document.getElementById('stat-direct');
        const hasMetrics = directStat && parseInt(directStat.textContent || '0') > 0;
        
        // Check if we have aircraft count from the status
        const hasAircraft = data.aircraft_count > 0;
        
        // Available only if: API has data, carriers selected, aircraft available, and we have calculations
        const isAvailable = data.available && data.api_responding && hasSelectedCarriers && hasAircraft && (hasGraphEdges || hasMetrics);
        
        if (isAvailable) {
            statusText.textContent = 'LOS Calculation: Available';
            statusIcon.style.color = '#00cc6f';
            statusIcon.classList.remove('error', 'checking');
            statusIcon.classList.add('available');
        } else if (!hasSelectedCarriers) {
            statusText.textContent = 'LOS Calculation: No carriers selected';
            statusIcon.style.color = '#ffaa00';
            statusIcon.classList.remove('available', 'error');
            statusIcon.classList.add('checking');
        } else if (!data.available || !data.api_responding) {
            statusText.textContent = 'LOS Calculation: Unavailable';
            statusIcon.style.color = '#ff4444';
            statusIcon.classList.remove('available', 'checking');
            statusIcon.classList.add('error');
        } else {
            statusText.textContent = 'LOS Calculation: No connections';
            statusIcon.style.color = '#ffaa00';
            statusIcon.classList.remove('available', 'error');
            statusIcon.classList.add('checking');
        }
    } catch (error) {
        console.error('Error checking LOS Calculation status:', error);
        updateLOSAPIStatus('Unavailable', 'error');
    }
}

// Update LOS Calculation status indicator
function updateLOSAPIStatus(text, type = 'checking') {
    const statusText = document.getElementById('los-api-status-text');
    const statusIcon = document.getElementById('los-api-status-icon');
    
    if (!statusText || !statusIcon) {
        return;
    }
    
    statusText.textContent = `LOS Calculation: ${text}`;
    
    if (type === 'error') {
        statusIcon.style.color = '#ff4444';
        statusIcon.classList.remove('available', 'checking');
        statusIcon.classList.add('error');
    } else if (type === 'available') {
        statusIcon.style.color = '#00cc6f';
        statusIcon.classList.remove('error', 'checking');
        statusIcon.classList.add('available');
    } else {
        statusIcon.style.color = '#ffaa00';
        statusIcon.classList.remove('available', 'error');
        statusIcon.classList.add('checking');
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

// Initialize graph visualization
function initializeGraph() {
    const container = document.getElementById('graph-container');
    graphSvg = d3.select('#graph-svg');
    
    // Create tooltip
    graphTooltip = d3.select('body').append('div')
        .attr('class', 'graph-tooltip')
        .style('opacity', 0);
}

// Update graph visualization
// graphData parameter is optional - if provided, use it; otherwise fetch from API
async function updateGraph(graphData = null) {
    if (selectedCarriers.size === 0) {
        if (graphSvg) {
            graphSvg.selectAll('*').remove();
        }
        return;
    }
    
    try {
        // If graphData not provided, fetch it from API
        if (!graphData) {
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
                    carrier_ranges: rangesObj,
                    include_airports: includeAirports
                })
            });
            
            if (!response.ok) {
                return;
            }
            
            graphData = await response.json();
        }
        
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
    
    // Create nodes - inside the container group
    // Separate airports (squares) from aircraft (circles)
    const aircraftNodes = data.nodes.filter(d => !d.is_airport);
    const airportNodes = data.nodes.filter(d => d.is_airport);
    
    // Create aircraft nodes (circles)
    const nodes = container.append('g')
        .attr('class', 'nodes')
        .selectAll('circle')
        .data(aircraftNodes, d => d.id)
        .enter()
        .append('circle')
        .attr('class', 'graph-node')
        .attr('r', 8)
        .attr('fill', 'rgba(0, 255, 136, 0.8)')
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
    
    // Create airport nodes (squares)
    const airports = container.append('g')
        .attr('class', 'airport-nodes')
        .selectAll('rect')
        .data(airportNodes, d => d.id)
        .enter()
        .append('rect')
        .attr('class', 'graph-airport-node')
        .attr('width', 16)
        .attr('height', 16)
        .attr('x', -8)
        .attr('y', -8)
        .attr('fill', 'rgba(255, 136, 0, 0.8)')
        .attr('stroke', '#cc6600')
        .attr('stroke-width', 2)
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag', dragged)
            .on('end', dragEnded))
        .on('mouseover', function(event, d) {
            graphTooltip.transition()
                .duration(200)
                .style('opacity', 0.9);
            graphTooltip.html(`${d.label}<br/>Airport`)
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
    
    // Store references to both node types for tick updates
    const allNodes = { circles: nodes, squares: airports };
    
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
        
        airports
            .attr('x', d => (d.x || 0) - 8)
            .attr('y', d => (d.y || 0) - 8);
        
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

// Handle window resize
window.addEventListener('resize', () => {
    if (graphSimulation && graphSvg) {
        const width = graphSvg.node().getBoundingClientRect().width || 800;
        const height = graphSvg.node().getBoundingClientRect().height || 500;
        graphSimulation.force('center', d3.forceCenter(width / 2, height / 2));
        graphSimulation.alpha(0.3).restart();
    }
    
    // Update Leaflet map size
    if (map) {
        map.invalidateSize();
    }
});

// Initialize Leaflet map
function initializeLeafletMap() {
    debugLog('main.js:1037', 'initializeLeafletMap entry', {
        hasLeaflet: typeof L !== 'undefined',
        hasMapElement: !!document.getElementById('map')
    });
    
    try {
        // Create map with dark theme tile layer
        map = L.map('map', {
            center: [39.8283, -98.5795], // Center of USA
            zoom: 4,
            zoomControl: true
        });
        
        // Use CartoDB Dark Matter tiles for dark theme
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 19
        }).addTo(map);
        
        satelliteFootprintLayer = L.layerGroup();
        
        debugLog('main.js:1055', 'Leaflet map initialized');
    } catch (e) {
        debugLog('main.js:1057', 'Leaflet initialization error', { error: e.message });
        throw e;
    }
}

// Update Leaflet map with aircraft and LOS connections
async function updateLeafletMap(aircraftList, graphData) {
    if (!map) {
        initializeLeafletMap();
    }
    
    // Clear existing markers and lines
    aircraftMarkers.forEach(marker => map.removeLayer(marker));
    losLines.forEach(line => map.removeLayer(line));
    aircraftMarkers = [];
    losLines = [];
    
    // Fetch airports if toggle is enabled
    let airports = {};
    if (includeAirports) {
        try {
            const airportsResp = await fetch('/api/airports');
            if (airportsResp.ok) {
                airports = await airportsResp.json();
            }
        } catch (error) {
            console.error('Error fetching airports:', error);
        }
    }
    
    // Create airport markers (distinct styling)
    const airportsByIcao = {};
    if (includeAirports && airports) {
        Object.entries(airports).forEach(([code, airport]) => {
            airportsByIcao[code] = airport;
            
            // Create airport marker with distinct styling (orange/red)
            const marker = L.circleMarker([airport.latitude, airport.longitude], {
                radius: 8,
                fillColor: '#ff8800',
                color: '#cc6600',
                weight: 2,
                opacity: 0.9,
                fillOpacity: 0.7
            });
            
            // Add popup with airport info
            marker.bindPopup(`
                <strong>${airport.name}</strong><br/>
                ICAO: ${code}<br/>
                Elevation: ${airport.elevation_m} m
            `);
            
            marker.addTo(map);
            aircraftMarkers.push(marker);
        });
    }
    
    // Create aircraft markers
    const aircraftByIcao = {};
    if (aircraftList && aircraftList.length > 0) {
        aircraftList.forEach(aircraft => {
            if (aircraft.latitude != null && aircraft.longitude != null) {
                aircraftByIcao[aircraft.icao24] = aircraft;
                
                // Create marker with custom icon
                const marker = L.circleMarker([aircraft.latitude, aircraft.longitude], {
                    radius: 6,
                    fillColor: '#00ff88',
                    color: '#00cc6f',
                    weight: 2,
                    opacity: 0.8,
                    fillOpacity: 0.6
                });
                
                // Add popup with aircraft info
                const callsign = aircraft.callsign || aircraft.icao24;
                const altitude = aircraft.geo_altitude ? (aircraft.geo_altitude / 1000).toFixed(2) + ' km' : 'Unknown';
                marker.bindPopup(`
                    <strong>${callsign}</strong><br/>
                    Carrier: ${aircraft.carrier_code || 'Unknown'}<br/>
                    Altitude: ${altitude}<br/>
                    ICAO24: ${aircraft.icao24}
                `);
                
                marker.addTo(map);
                aircraftMarkers.push(marker);
            }
        });
    }
    
    // Draw LOS connection lines
    if (graphData && graphData.edges) {
        // Calculate line width range
        const distances = graphData.edges.map(e => e.distance);
        const maxDistance = distances.length > 0 ? Math.max(...distances) : 1;
        const minDistance = distances.length > 0 ? Math.min(...distances) : 1;
        const distanceRange = maxDistance - minDistance || 1;
        
        graphData.edges.forEach(edge => {
            let fromPos = null;
            let toPos = null;
            
            // Check if edge is from/to airport or aircraft
            if (airportsByIcao[edge.from]) {
                const airport = airportsByIcao[edge.from];
                fromPos = [airport.latitude, airport.longitude];
            } else if (aircraftByIcao[edge.from]) {
                const ac = aircraftByIcao[edge.from];
                if (ac.latitude != null && ac.longitude != null) {
                    fromPos = [ac.latitude, ac.longitude];
                }
            }
            
            if (airportsByIcao[edge.to]) {
                const airport = airportsByIcao[edge.to];
                toPos = [airport.latitude, airport.longitude];
            } else if (aircraftByIcao[edge.to]) {
                const ac = aircraftByIcao[edge.to];
                if (ac.latitude != null && ac.longitude != null) {
                    toPos = [ac.latitude, ac.longitude];
                }
            }
            
            if (fromPos && toPos) {
                // Calculate line width based on distance (inverse: shorter = thicker)
                const normalized = 1 - ((edge.distance - minDistance) / distanceRange);
                const lineWidth = 1 + (normalized * 3); // 1px to 4px
                
                // Use different color for airport connections
                const isAirportConnection = airportsByIcao[edge.from] || airportsByIcao[edge.to];
                const lineColor = isAirportConnection ? '#ff8800' : '#00ff88';
                
                const line = L.polyline(
                    [fromPos, toPos],
                    {
                        color: lineColor,
                        weight: lineWidth,
                        opacity: 0.6
                    }
                );
                
                line.bindPopup(`Distance: ${edge.distance.toFixed(2)} km`);
                line.addTo(map);
                losLines.push(line);
            }
        });
    }
    
    // Fit map to show all markers
    if (aircraftMarkers.length > 0) {
        const group = new L.featureGroup(aircraftMarkers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

// Update LOS metrics display
function updateLOSMetrics(metrics) {
    if (!metrics) {
        // Clear all metrics
        document.getElementById('metric-total-pairs').textContent = '0';
        document.getElementById('metric-los-pairs').textContent = '0';
        document.getElementById('metric-los-percentage').textContent = '0%';
        document.getElementById('metric-avg-los-distance').textContent = '0 km';
        document.getElementById('metric-min-los-distance').textContent = '0 km';
        document.getElementById('metric-max-los-distance').textContent = '0 km';
        document.getElementById('metric-graph-density').textContent = '0';
        document.getElementById('metric-avg-degree').textContent = '0';
        document.getElementById('metric-clustering').textContent = '0';
        document.getElementById('metric-components').textContent = '0';
        document.getElementById('metric-largest-component').textContent = '0';
        document.getElementById('metric-path-length').textContent = '0';
        document.getElementById('metric-avg-altitude').textContent = '0 km';
        document.getElementById('metric-avg-altitude-diff').textContent = '0 km';
        document.getElementById('metric-low-altitude').textContent = '0';
        document.getElementById('metric-medium-altitude').textContent = '0';
        document.getElementById('metric-high-altitude').textContent = '0';
        document.getElementById('metric-bounding-box-container').style.display = 'none';
        return;
    }
    
    // Coverage metrics
    const coverage = metrics.coverage || {};
    document.getElementById('metric-total-pairs').textContent = coverage.total_pairs || 0;
    document.getElementById('metric-los-pairs').textContent = coverage.los_pairs_count || 0;
    document.getElementById('metric-los-percentage').textContent = (coverage.los_pairs_percentage || 0) + '%';
    document.getElementById('metric-avg-los-distance').textContent = (coverage.average_los_distance_km || 0) + ' km';
    document.getElementById('metric-min-los-distance').textContent = (coverage.min_los_distance_km || 0) + ' km';
    document.getElementById('metric-max-los-distance').textContent = (coverage.max_los_distance_km || 0) + ' km';
    
    // Connectivity metrics
    const connectivity = metrics.connectivity || {};
    document.getElementById('metric-graph-density').textContent = (connectivity.graph_density || 0).toFixed(4);
    document.getElementById('metric-avg-degree').textContent = (connectivity.average_node_degree || 0).toFixed(2);
    document.getElementById('metric-clustering').textContent = (connectivity.clustering_coefficient || 0).toFixed(4);
    document.getElementById('metric-components').textContent = connectivity.connected_components_count || 0;
    document.getElementById('metric-largest-component').textContent = connectivity.largest_component_size || 0;
    document.getElementById('metric-path-length').textContent = (connectivity.average_path_length || 0).toFixed(2);
    
    // Geographic metrics
    const geographic = metrics.geographic || {};
    document.getElementById('metric-avg-altitude').textContent = (geographic.average_altitude_km || 0) + ' km';
    document.getElementById('metric-avg-altitude-diff').textContent = (geographic.average_altitude_diff_km || 0) + ' km';
    const altDist = geographic.altitude_distribution || {};
    document.getElementById('metric-low-altitude').textContent = altDist.low_band_count || 0;
    document.getElementById('metric-medium-altitude').textContent = altDist.medium_band_count || 0;
    document.getElementById('metric-high-altitude').textContent = altDist.high_band_count || 0;
    
    // Bounding box
    if (geographic.bounding_box) {
        const bb = geographic.bounding_box;
        document.getElementById('metric-bounding-box').textContent = 
            `${bb.min_latitude.toFixed(2)}°N, ${bb.min_longitude.toFixed(2)}°E to ${bb.max_latitude.toFixed(2)}°N, ${bb.max_longitude.toFixed(2)}°E`;
        document.getElementById('metric-bounding-box-container').style.display = 'block';
    } else {
        document.getElementById('metric-bounding-box-container').style.display = 'none';
    }
}

