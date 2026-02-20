## 1. Data Model and Storage
- [x] 1.1 Define Net schema (id, name, frequency, band, description)
- [x] 1.2 Define Node/Radio schema (id, label, configured_nets, assigned_nets, frequency_capability)
- [x] 1.3 Implement in-memory or persistent storage for nets and nodes
- [x] 1.4 Add API endpoints to CRUD nets and nodes

## 2. Net Connectivity Logic
- [x] 2.1 Compute net connectivity (nets connected via shared nodes)
- [x] 2.2 Compute connected net groups (transitive closure)
- [x] 2.3 Add API endpoint to return net connectivity and bridge nodes

## 3. Compliance and Non-Compliant Detection
- [x] 3.1 Implement non-compliant detection: assigned_nets - configured_nets ≠ ∅
- [x] 3.2 Add API endpoint to return compliance status per net and per node
- [x] 3.3 Add API endpoint to list radios not set up to join their assigned nets

## 4. UI Integration
- [x] 4.1 Add UI to manage nets (create, edit, list)
- [x] 4.2 Add UI to manage nodes and their net assignments/configurations
- [x] 4.3 Add UI to view net connectivity (which nets are connected, bridge nodes)
- [x] 4.4 Add UI to view and filter non-compliant radios
