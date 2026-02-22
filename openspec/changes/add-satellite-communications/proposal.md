# Change: Add Satellite Communications Tracking

## Why
Aircraft use satellite links only when flying. Operators need to track planned satellite usage times per node, see total nodes per satellite, and identify potential saturation when too many users fall within the same satellite footprint. The system must use simple, straightforward calculations—not full link budget or satellite orbital mechanics.

## What Changes
- Add satellite entity with footprint (simple geometric representation on map—e.g., circle or polygon, not orbital mechanics)
- Add per-node planned satellite usage: which satellite, time window (when the node plans to use the link; planes only when flying)
- Show total nodes per satellite (aggregate count)
- Add satellite footprint as a selectable map layer to visualize coverage
- Identify potential saturation: highlight or flag when too many nodes are in the same footprint
- Keep calculations simple: footprint as static or time-simplified geometry, no link budget, no full orbital propagation

## Impact
- Affected specs: New capability `satellite-communications`
- Affected code: New data model, API endpoints, map layer for footprints, saturation logic
- Data: Node-level planned usage (satellite + time window)
