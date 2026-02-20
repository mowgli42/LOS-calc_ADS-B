# Change: Add Radio Net Configuration

## Why
Establish shared nets where radios can listen and people talk on a common frequency. The system currently reports frequency bands but does not capture per-node configuration, net connectivity, or identify radios that are misconfigured. Operators need visibility into which nets are connected (via bridge radios) and which radios are not set up to join their required nets.

## What Changes
- Add radio net model: named nets with frequency, band, and assigned radios
- Add per-node data capture: for each radio/node, capture configured nets, frequency capability, and assignment status (not just frequency band)
- Add net connectivity: identify which nets are connected (share participants or can relay between them)
- Add non-compliant radio detection: identify radios expected to join a net but not configured for it
- Add API and UI support to manage nets, nodes, and view connectivity/compliance status

## Impact
- Affected specs: New capability `radio-net-configuration`
- Affected code: New data model, API endpoints, and UI components; may extend existing graph/connectivity logic
- Data source: Node/radio configuration data (source TBD—manual entry, config import, or integration)
