## Context

The ADS-B LOS Calculator currently computes pairwise LOS distances for all selected-carrier aircraft and surfaces them only as aggregate charts (distance histogram, connection distribution) and summary metrics (coverage, connectivity, geographic panels). The raw pair-level data returned by `calculate_all_pair_distances()` and `calculate_airport_to_aircraft_distances()` is already computed on the backend but is either truncated (limited to 100 pairs in the `/api/distances` response) or never sent to the client in tabular form. Analysts need to inspect, sort, and filter individual pair records to find specific aircraft, identify outliers, or validate aggregate results.

## Goals / Non-Goals

**Goals:**
- Expose full per-pair LOS data in a dedicated API endpoint with server-side pagination
- Render a sortable, filterable HTML table in the existing UI that matches the dark theme
- Support sorting on every column (callsign, carrier, distance, radio horizon, LOS status, altitude)
- Support filtering by carrier code, within-LOS status, and minimum/maximum distance
- Include airport-to-aircraft pairs when airports are enabled

**Non-Goals:**
- Server-side sorting/filtering (client-side is sufficient for the expected data volume of a few thousand pairs)
- CSV/JSON export functionality (can be added later)
- Editable cells or inline configuration
- Virtual scrolling or infinite pagination (simple page-size limit is adequate)

## Decisions

### Decision 1: New dedicated API endpoint vs. extending existing `/api/distances`

**Choice:** New `POST /api/los-table` endpoint.

**Rationale:** The existing `/api/distances` endpoint is tuned for the histogram visualization — it bins data and truncates to 100 results. A separate endpoint avoids breaking existing consumers and can return the full, un-truncated pair list with all fields the table needs. The endpoint reuses the same `calculate_all_pair_distances()` and `calculate_airport_to_aircraft_distances()` functions.

**Alternatives considered:** Extending `/api/distances` with a `?format=table` query param. Rejected because it would complicate the existing endpoint's response shape and require versioning the contract.

### Decision 2: Client-side sorting and filtering

**Choice:** All sorting and filtering happens in the browser via vanilla JavaScript.

**Rationale:** With the top-25 carriers selected, the maximum pair count is on the order of a few thousand (n*(n-1)/2 for ~100-200 aircraft). This fits comfortably in browser memory and allows instant sort/filter without round-trips. No additional JS libraries are needed — `Array.prototype.sort()` and basic DOM manipulation are sufficient, matching the existing vanilla JS approach in `main.js`.

### Decision 3: Table rendering approach

**Choice:** Vanilla HTML `<table>` with dynamically generated rows from JS, styled to match the existing dark theme.

**Rationale:** The project uses no frontend framework. Adding a data-grid library (e.g., AG Grid, DataTables) would introduce a new CDN dependency and complexity. A plain HTML table with click-to-sort headers and a small filter bar is consistent with the existing minimalistic approach.

## Risks / Trade-offs

- **Large pair counts with many carriers selected** → The table could have thousands of rows. Mitigation: default to showing the first 100 rows with a "Show more" / page-size control. The API returns all data; pagination is client-side.
- **Performance of re-rendering on sort/filter** → Rebuilding the DOM for a few thousand rows on each sort is fast in modern browsers. If it becomes a bottleneck, rows can be virtualized in a follow-up change.
- **Data freshness** → The table data is fetched once when carriers are selected and updates on the same 15-minute refresh cycle as other panels. No separate refresh mechanism is needed.
