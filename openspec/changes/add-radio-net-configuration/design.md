# Design: Radio Net Configuration

## Context
Tactical and operational radio nets require radios to share a common frequency. Operators need to:
1. Capture per-node data (which nets each radio is configured for and assigned to)
2. Identify which nets are connected (share participants and can relay traffic)
3. Identify radios that should be on a net but are not configured for it

The current system focuses on aircraft ADS-B and line-of-sight connectivity. Radio net configuration is a complementary capability for managing voice/data radio networks.

## Goals / Non-Goals
- **Goals**: Per-node capture, net connectivity, non-compliant radio identification
- **Non-Goals**: Real-time radio monitoring, cryptographic key management, hardware radio control

## Decisions

### Decision: Net and Node Data Model
**What**: 
- **Net**: `id`, `name`, `frequency_mhz`, `band` (e.g., VHF, UHF), `description`
- **Node**: `id`, `label`, `configured_nets` (list of net ids the radio can join), `assigned_nets` (list of net ids the operator expects), `frequency_capability` (optional supported bands)

**Why**: Separating configured vs assigned nets allows compliance checking. Configured = radio has the channel; Assigned = operator expects participation.

**Alternatives considered**: Single "nets" list per node—rejected because it does not support compliance (expected vs actual).

### Decision: Net Connectivity Definition
**What**: Two nets are **connected** if they share at least one node that is configured for both nets. Connected net groups use transitive closure (net A–B and B–C implies A–B–C in one group).

**Why**: A node on both nets can relay traffic, effectively connecting the nets operationally.

**Alternatives considered**: Frequency proximity—rejected; connectivity is about shared participants, not spectrum adjacency.

### Decision: Data Source
**What**: Initial implementation uses in-memory storage with API-driven CRUD. Support config import (e.g., JSON/CSV) for bulk load.

**Why**: Keeps scope manageable; real-time integration with radio config systems can be added later.

## Risks / Trade-offs
- **Risk**: Manual data entry may be error-prone → Mitigation: Support config import, validation on net assignment
- **Trade-off**: In-memory storage loses data on restart → Mitigation: Add file-based or DB persistence in follow-up

## Migration Plan
- New capability; no migration of existing data. May later integrate with aircraft/nodes if radios are associated with aircraft or ground stations.

## Open Questions
- Source of node/radio configuration: manual only, or integration with existing provisioning?
- Relationship to aircraft ADS-B nodes: separate domain, or extend aircraft as potential "nodes" on nets?
