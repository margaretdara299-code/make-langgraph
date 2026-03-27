"""
Workflow Validator — structural checks before graph building.
Returns a validation result with errors list.
"""
from __future__ import annotations
from app.engine.models import WorkflowDef


def validate_workflow(workflow_json: dict) -> dict:
    """
    Validate a workflow JSON definition for structural correctness.

    Returns:
        { "valid": bool, "errors": list[str], "warnings": list[str] }
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ── 1. Parse with Pydantic ─────────────────────────────────────────
    try:
        wf = WorkflowDef(**workflow_json)
    except Exception as e:
        return {"valid": False, "errors": [f"Invalid workflow structure: {e}"], "warnings": []}

    # ── 2. Must have at least one node ─────────────────────────────────
    if not wf.nodes:
        errors.append("Workflow must contain at least one node.")
        return {"valid": False, "errors": errors, "warnings": warnings}

    # ── 3. Unique node IDs ─────────────────────────────────────────────
    node_ids = [n.id for n in wf.nodes]
    seen = set()
    for nid in node_ids:
        if nid in seen:
            errors.append(f"Duplicate node id: '{nid}'")
        seen.add(nid)
    node_id_set = set(node_ids)

    # ── 4. Edge source/target reference valid nodes ────────────────────
    for edge_id, edge in wf.connections.items():
        if edge.source not in node_id_set:
            errors.append(f"Connection '{edge_id}': source '{edge.source}' not found.")
        if edge.target not in node_id_set:
            errors.append(f"Connection '{edge_id}': target '{edge.target}' not found.")

    # ── 5. Action check (Removed ACTION_REGISTRY enforcement) ──────────
    pass

    # ── 6. Triggers and Ends validation (DB specific logic) ────────────
    triggers = [n for n in wf.nodes if n.type and n.type.startswith("trigger.")]
    if len(triggers) == 0:
        warnings.append("No trigger.* node found. Entry point will be the first node.")
    
    # ── 7. Entry node detection ────────────────────────────────────────
    targets = {e.target for e in wf.connections.values()}
    entry_nodes = [n.id for n in wf.nodes if n.id not in targets]
    if not entry_nodes:
        errors.append("No entry node found — every node is a target of some edge (possible cycle).")

    # ── 8. Terminal nodes exist (nodes with no outgoing edge) ──────────
    sources = {e.source for e in wf.connections.values()}
    terminal_nodes = [n.id for n in wf.nodes if n.id not in sources]
    if not terminal_nodes:
        warnings.append("No terminal node found — every node has outgoing edges.")

    # ── 9. Orphan detection (nodes unreachable) ────────────────────────
    connected = sources | targets
    for node in wf.nodes:
        if node.id not in connected and len(wf.nodes) > 1:
            warnings.append(f"Node '{node.id}' is isolated.")

    # ── 10. Cycle Detection (DFS) ──────────────────────────────────────
    adjacency_by_node_id: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for edge in wf.connections.values():
        if edge.source in adjacency_by_node_id:
            adjacency_by_node_id[edge.source].append(edge.target)
    
    if _detect_cycle(node_ids, adjacency_by_node_id):
        errors.append("Flow graph contains a cycle.")

    # ── 11. Conditional edge validation ────────────────────────────────
    for edge_id, edge in wf.connections.items():
        cond_data = edge.condition or {}
        cond_value = cond_data.get("value")
        if cond_value and cond_value not in ("true", "false") and not edge.is_default:
            # We only warn here as complex expressions might be allowed later
            warnings.append(f"Connection '{edge_id}': custom condition '{cond_value}' found.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "node_count": len(wf.nodes),
        "edge_count": len(wf.connections),
        "entry_nodes": entry_nodes if not errors else [],
        "terminal_nodes": terminal_nodes if not errors else [],
    }


def _detect_cycle(
    node_ids: list[str],
    adjacency_by_node_id: dict[str, list[str]],
) -> bool:
    """Formal DFS cycle detection."""
    has_cycle = False
    visited_node_ids: set[str] = set()
    active_traversal_node_ids: set[str] = set()

    def traverse_depth_first(node_id: str) -> None:
        nonlocal has_cycle

        if node_id in active_traversal_node_ids:
            has_cycle = True
            return

        if node_id in visited_node_ids or has_cycle:
            return

        visited_node_ids.add(node_id)
        active_traversal_node_ids.add(node_id)

        for adjacent_node_id in adjacency_by_node_id.get(node_id, []):
            traverse_depth_first(adjacent_node_id)

        active_traversal_node_ids.remove(node_id)

    for node_id in node_ids:
        if node_id not in visited_node_ids:
            traverse_depth_first(node_id)

    return has_cycle
