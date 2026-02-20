"""
Satellite communications tracking: satellites, planned usage, aggregation, saturation.
Simple calculations only—no link budget or orbital mechanics.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional


# In-memory storage
_satellites: Dict[str, dict] = {}
_planned_usage: List[dict] = []  # [{node_id, satellite_id, start_time, end_time}]
DEFAULT_SATURATION_THRESHOLD = 10


def _generate_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}" if prefix else uuid.uuid4().hex[:8]


def _parse_dt(s: str) -> Optional[datetime]:
    """Parse ISO datetime string."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def create_satellite(
    name: str,
    footprint_center_lat: float,
    footprint_center_lon: float,
    footprint_radius_km: float,
) -> dict:
    """Create a satellite with circle footprint."""
    sat_id = _generate_id("sat_")
    sat = {
        "id": sat_id,
        "name": name,
        "footprint_center_lat": footprint_center_lat,
        "footprint_center_lon": footprint_center_lon,
        "footprint_radius_km": footprint_radius_km,
    }
    _satellites[sat_id] = sat
    return sat


def update_satellite(sat_id: str, **kwargs) -> Optional[dict]:
    """Update a satellite."""
    if sat_id not in _satellites:
        return None
    allowed = {"name", "footprint_center_lat", "footprint_center_lon", "footprint_radius_km"}
    for k, v in kwargs.items():
        if k in allowed and k in _satellites[sat_id]:
            _satellites[sat_id][k] = v
    return _satellites[sat_id]


def get_satellite(sat_id: str) -> Optional[dict]:
    return _satellites.get(sat_id)


def list_satellites() -> List[dict]:
    return list(_satellites.values())


def delete_satellite(sat_id: str) -> bool:
    if sat_id not in _satellites:
        return False
    del _satellites[sat_id]
    global _planned_usage
    _planned_usage = [u for u in _planned_usage if u.get("satellite_id") != sat_id]
    return True


def add_planned_usage(
    node_id: str,
    satellite_id: str,
    start_time: str,
    end_time: str,
) -> Optional[dict]:
    """Add planned satellite usage for a node. Times as ISO strings."""
    if satellite_id not in _satellites:
        return None
    usage_id = _generate_id("usage_")
    usage = {
        "id": usage_id,
        "node_id": node_id,
        "satellite_id": satellite_id,
        "start_time": start_time,
        "end_time": end_time,
    }
    _planned_usage.append(usage)
    return usage


def delete_planned_usage(usage_id: str) -> bool:
    """Delete a planned usage by id."""
    global _planned_usage
    before = len(_planned_usage)
    _planned_usage = [u for u in _planned_usage if u.get("id") != usage_id]
    return len(_planned_usage) < before


def list_planned_usage(node_id: Optional[str] = None, satellite_id: Optional[str] = None) -> List[dict]:
    """List planned usage, optionally filtered by node or satellite."""
    result = _planned_usage
    if node_id:
        result = [u for u in result if u.get("node_id") == node_id]
    if satellite_id:
        result = [u for u in result if u.get("satellite_id") == satellite_id]
    return result


def _usage_overlaps_time(usage: dict, query_dt: datetime) -> bool:
    """Check if usage overlaps the query time."""
    start = _parse_dt(usage.get("start_time"))
    end = _parse_dt(usage.get("end_time"))
    if not start or not end:
        return False
    return start <= query_dt <= end


def get_nodes_per_satellite(
    query_time: Optional[str] = None,
    saturation_threshold: int = DEFAULT_SATURATION_THRESHOLD,
) -> dict:
    """
    Return total nodes per satellite for a given time.
    If query_time is None, use now.
    Also returns saturation status.
    """
    query_dt = _parse_dt(query_time) if query_time else datetime.now()

    counts: Dict[str, int] = {s["id"]: 0 for s in _satellites.values()}
    node_ids_per_sat: Dict[str, set] = {s["id"]: set() for s in _satellites.values()}

    for usage in _planned_usage:
        if not _usage_overlaps_time(usage, query_dt):
            continue
        sat_id = usage.get("satellite_id")
        node_id = usage.get("node_id")
        if sat_id in counts and node_id:
            node_ids_per_sat[sat_id].add(node_id)
            counts[sat_id] = len(node_ids_per_sat[sat_id])

    result = []
    for sat in _satellites.values():
        sat_id = sat["id"]
        count = counts.get(sat_id, 0)
        saturated = count > saturation_threshold
        result.append({
            **sat,
            "node_count": count,
            "node_ids": list(node_ids_per_sat.get(sat_id, [])),
            "saturated": saturated,
        })

    return {
        "query_time": query_dt.isoformat(),
        "saturation_threshold": saturation_threshold,
        "satellites": result,
    }


def get_satellite_footprints() -> List[dict]:
    """Return satellites with footprint data for map rendering."""
    return list(_satellites.values())
