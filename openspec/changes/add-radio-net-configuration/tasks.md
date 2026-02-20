## 1. Data Model and Storage
- [ ] 1.1 Define Net schema (id, name, frequency, band, description)
- [ ] 1.2 Define Node/Radio schema (id, label, configured_nets, assigned_nets, frequency_capability)
- [ ] 1.3 Implement in-memory or persistent storage for nets and nodes
- [ ] 1.4 Add API endpoints to CRUD nets and nodes

## 2. Net Connectivity Logic
- [ ] 2.1 Compute net connectivity (nets connected via shared nodes)
- [ ] 2.2 Compute connected net groups (transitive closure)
- [ ] 2.3 Add API endpoint to return net connectivity and bridge nodes

## 3. Compliance and Non-Compliant Detection
- [ ] 3.1 Implement non-compliant detection: assigned_nets - configured_nets ≠ ∅
- [ ] 3.2 Add API endpoint to return compliance status per net and per node
- [ ] 3.3 Add API endpoint to list radios not set up to join their assigned nets

## 4. UI Integration
- [ ] 4.1 Add UI to manage nets (create, edit, list)
- [ ] 4.2 Add UI to manage nodes and their net assignments/configurations
- [ ] 4.3 Add UI to view net connectivity (which nets are connected, bridge nodes)
- [ ] 4.4 Add UI to view and filter non-compliant radios
