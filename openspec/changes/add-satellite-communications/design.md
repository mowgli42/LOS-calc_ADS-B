# Design: Satellite Communications Tracking

## Context
Aircraft use satellite communications only when flying. Operators need to:
1. Track when each node (plane) plans to use which satellite
2. See total nodes per satellite
3. Visualize satellite footprints on the map
4. Identify saturation (too many users in the same footprint)

Calculations must be simple—no full link budget, no orbital mechanics.

## Goals / Non-Goals
- **Goals**: Planned usage tracking, node counts per satellite, footprint visualization, saturation identification
- **Non-Goals**: Full orbital mechanics, link budget calculations, real-time satellite position propagation, RF modeling

## Decisions

### Decision: Satellite Footprint Model
**What**: Represent each satellite's footprint as a static or time-simplified geometric shape on the map:
- **Option A**: Circle (center lat/lon, radius km)—simplest
- **Option B**: Polygon (list of lat/lon points)—more flexible for irregular beams

Start with **circle** (center + radius) for simplicity. Radius represents nominal beam coverage.

**Why**: Avoids orbital mechanics. Operators can define footprints based on expected coverage, not propagated orbits.

### Decision: Planned Usage Data Model
**What**: Per node, store:
- `satellite_id`: which satellite
- `start_time`, `end_time`: planned usage window (when the plane will be flying and using the link)

Nodes (e.g., aircraft) add this data when they plan to use a satellite link.

**Why**: "Planes only use satellite when flying" implies time-bounded usage. Simple start/end captures the planned window.

### Decision: Saturation Detection
**What**: For a given time (or time range), count nodes in each satellite's footprint. Flag saturation when count exceeds a configurable threshold (e.g., 10, 20 users).

**Why**: Simple count-based logic. No capacity modeling—operators set threshold based on their operational limits.

### Decision: Footprint as Map Layer
**What**: Satellite footprints as a selectable layer on the existing Leaflet map. User can toggle layer on/off. Each footprint drawn as a circle (or polygon). Optionally color or label by node count / saturation status.

**Why**: Integrates with existing map; no new map framework.

## Risks / Trade-offs
- **Risk**: Static footprint may not match real coverage → Mitigation: Document as planning aid; operators update footprint definitions as needed
- **Trade-off**: No orbital propagation → Explicit non-goal; keeps scope manageable

## Migration Plan
- New capability; no migration of existing data. May reference nodes from radio net or aircraft systems.

## Open Questions
- Source of satellite footprint definitions: manual entry, or import from external catalog?
- Relationship to aircraft/nodes: extend existing node model or separate satellite-planning entities?
