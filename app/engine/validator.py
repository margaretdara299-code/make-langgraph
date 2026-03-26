"""
Workflow Validator — structural checks before graph building.
Returns a validation result with errors list.
"""
from __future__ import annotations
from app.engine.models import WorkflowDef
from app.engine.action_registry import ACTION_REGISTRY


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

    # ── 5. All actionKey exist in ACTION_REGISTRY ──────────────────────
    for node in wf.nodes:
        action_key = node.data.actionKey
        if action_key and action_key not in ACTION_REGISTRY:
            errors.append(
                f"Node '{node.id}': unknown actionKey '{action_key}'. "
                f"Available: {list(ACTION_REGISTRY.keys())}"
            )

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

    # ── 10. Conditional edge validation ────────────────────────────────
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
