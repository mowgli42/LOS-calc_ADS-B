"""
Radio net configuration: nets, nodes, connectivity, and compliance.
"""

import uuid
from typing import Dict, List, Set, Tuple
from collections import defaultdict


# In-memory storage
_nets: Dict[str, dict] = {}
_nodes: Dict[str, dict] = {}


def _generate_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}" if prefix else uuid.uuid4().hex[:8]


def create_net(name: str, frequency_mhz: float, band: str = "VHF", description: str = "") -> dict:
    """Create a net. Returns net dict."""
    net_id = _generate_id("net_")
    net = {
        "id": net_id,
        "name": name,
        "frequency_mhz": frequency_mhz,
        "band": band,
        "description": description or "",
    }
    _nets[net_id] = net
    return net


def update_net(net_id: str, **kwargs) -> dict:
    """Update a net. Returns updated net or None if not found."""
    if net_id not in _nets:
        return None
    for k, v in kwargs.items():
        if k in _nets[net_id]:
            _nets[net_id][k] = v
    return _nets[net_id]


def get_net(net_id: str) -> dict:
    return _nets.get(net_id)


def list_nets() -> List[dict]:
    return list(_nets.values())


def delete_net(net_id: str) -> bool:
    if net_id not in _nets:
        return False
    del _nets[net_id]
    # Remove net from all nodes
    for node in _nodes.values():
        node["configured_nets"] = [n for n in node.get("configured_nets", []) if n != net_id]
        node["assigned_nets"] = [n for n in node.get("assigned_nets", []) if n != net_id]
    return True


def create_node(label: str, configured_nets: List[str] = None, assigned_nets: List[str] = None,
                frequency_capability: List[str] = None) -> dict:
    """Create a node (radio). Returns node dict."""
    node_id = _generate_id("node_")
    node = {
        "id": node_id,
        "label": label or node_id,
        "configured_nets": list(configured_nets or []),
        "assigned_nets": list(assigned_nets or []),
        "frequency_capability": list(frequency_capability or []),
    }
    _nodes[node_id] = node
    return node


def update_node(node_id: str, **kwargs) -> dict:
    """Update a node. Returns updated node or None if not found."""
    if node_id not in _nodes:
        return None
    for k, v in kwargs.items():
        if k in _nodes[node_id]:
            if k in ("configured_nets", "assigned_nets", "frequency_capability"):
                _nodes[node_id][k] = list(v) if v else []
            else:
                _nodes[node_id][k] = v
    return _nodes[node_id]


def get_node(node_id: str) -> dict:
    return _nodes.get(node_id)


def list_nodes() -> List[dict]:
    return list(_nodes.values())


def delete_node(node_id: str) -> bool:
    if node_id not in _nodes:
        return False
    del _nodes[node_id]
    return True


def _compute_net_connectivity() -> Tuple[Dict[str, Set[str]], List[Set[str]]]:
    """
    Compute net-to-net connectivity via shared nodes.
    Returns:
        - connected_pairs: {net_id: set of net_ids connected to it}
        - connected_groups: list of sets of net_ids (transitive closure)
    """
    net_to_nodes: Dict[str, Set[str]] = defaultdict(set)
    for node_id, node in _nodes.items():
        for net_id in node.get("configured_nets", []):
            if net_id in _nets:
                net_to_nodes[net_id].add(node_id)

    # Build net connectivity graph: two nets connected if they share a node
    connected_pairs: Dict[str, Set[str]] = defaultdict(set)
    for net1 in _nets:
        for net2 in _nets:
            if net1 == net2:
                continue
            shared = net_to_nodes[net1] & net_to_nodes[net2]
            if shared:
                connected_pairs[net1].add(net2)
                connected_pairs[net2].add(net1)

    # Transitive closure: connected groups
    visited = set()
    connected_groups = []

    def dfs(net: str, group: Set[str]) -> None:
        if net in visited:
            return
        visited.add(net)
        group.add(net)
        for neighbor in connected_pairs.get(net, set()):
            dfs(neighbor, group)

    for net_id in _nets:
        if net_id not in visited:
            group = set()
            dfs(net_id, group)
            connected_groups.append(group)

    return dict(connected_pairs), connected_groups


def get_net_connectivity() -> dict:
    """Return net connectivity: which nets are connected, bridge nodes, and connected groups."""
    connected_pairs, connected_groups = _compute_net_connectivity()

    # Build bridge nodes: for each net pair, list nodes that bridge them
    bridge_nodes: Dict[str, Dict[str, List[str]]] = {}
    for net1 in _nets:
        for net2 in connected_pairs.get(net1, set()):
            if net1 < net2:  # Avoid duplicate
                key = f"{net1}|{net2}"
            else:
                key = f"{net2}|{net1}"
            if key not in bridge_nodes:
                bridges = [
                    nid for nid, node in _nodes.items()
                    if net1 in node.get("configured_nets", []) and net2 in node.get("configured_nets", [])
                ]
                bridge_nodes[key] = {"nets": [net1, net2], "bridge_nodes": bridges}

    return {
        "connected_pairs": {k: list(v) for k, v in connected_pairs.items()},
        "connected_groups": [list(g) for g in connected_groups],
        "bridge_nodes": list(bridge_nodes.values()),
    }


def _is_compliant(node: dict) -> bool:
    """Node is compliant if assigned_nets ⊆ configured_nets."""
    assigned = set(node.get("assigned_nets", []))
    configured = set(node.get("configured_nets", []))
    return assigned <= configured


def get_compliance_status() -> dict:
    """Return compliance status per net and per node."""
    per_net = {}
    for net_id, net in _nets.items():
        compliant = []
        non_compliant = []
        optional = []  # configured but not assigned
        for node_id, node in _nodes.items():
            configured = net_id in node.get("configured_nets", [])
            assigned = net_id in node.get("assigned_nets", [])
            if configured and assigned:
                compliant.append(node_id)
            elif assigned and not configured:
                non_compliant.append(node_id)
            elif configured and not assigned:
                optional.append(node_id)
        per_net[net_id] = {
            "compliant": compliant,
            "non_compliant": non_compliant,
            "optional": optional,
        }

    per_node = {}
    for node_id, node in _nodes.items():
        assigned = set(node.get("assigned_nets", []))
        configured = set(node.get("configured_nets", []))
        missing = assigned - configured
        per_node[node_id] = {
            "compliant": _is_compliant(node),
            "missing_nets": list(missing),
        }

    return {
        "per_net": per_net,
        "per_node": per_node,
    }


def get_non_compliant_nodes() -> List[dict]:
    """Return list of nodes not configured to join at least one assigned net."""
    result = []
    for node_id, node in _nodes.items():
        assigned = set(node.get("assigned_nets", []))
        configured = set(node.get("configured_nets", []))
        missing = assigned - configured
        if missing:
            result.append({
                "node_id": node_id,
                "label": node.get("label", node_id),
                "assigned_nets": list(assigned),
                "configured_nets": list(configured),
                "missing_nets": list(missing),
            })
    return result
