"""
compiler/validator.py — Structural validation for workflow definitions.
Checks node integrity, edge references, cycles, and terminal node requirements.
"""
from __future__ import annotations
from app.engine.models import WorkflowDef


def validate_workflow(workflow_json: dict) -> dict:
    """
    Validate a workflow JSON definition.
    Currently runs in completely relaxed mode per user request: structural graph theory 
    issues (like orphans or missing end nodes) do not block compilation or execution.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Parse with Pydantic (structural JSON check)
    try:
        wf = WorkflowDef(**workflow_json)
    except Exception as e:
        return {"valid": False, "errors": [f"Invalid workflow JSON format: {e}"], "warnings": []}

    # 2. Relaxed Mode: Do not block empty workflows
    if not wf.nodes:
        warnings.append("Workflow contains no nodes. Execution will bypass cleanly.")
        return {"valid": True, "errors": errors, "warnings": warnings, "node_count": 0, "edge_count": 0}

    # Gather data for warnings mapping
    node_ids = {n.id for n in wf.nodes}
    sources = set()
    targets = set()
    
    # Check edges
    for edge_id, edge in wf.connections.items():
        if edge.source not in node_ids:
            warnings.append(f"Connection '{edge_id}': source '{edge.source}' not found.")
        if edge.target not in node_ids:
            warnings.append(f"Connection '{edge_id}': target '{edge.target}' not found.")
        sources.add(edge.source)
        targets.add(edge.target)

    # Terminal nodes detection
    terminal_nodes = [n.id for n in wf.nodes if n.id not in sources]
    end_nodes = [n for n in wf.nodes if n.type and n.type.startswith("end.")]
    if not end_nodes:
        warnings.append("No explicit terminal node of type 'end.*' found. Leaf nodes will auto-route to END.")

    # Cycle Detection
    adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for edge in wf.connections.values():
        if edge.source in adjacency:
            adjacency[edge.source].append(edge.target)

    if _has_cycle(list(node_ids), adjacency):
        warnings.append("Flow graph contains a cycle.")

    return {
        "valid": True,  # ALWAYS TRUE UNLESS JSON PARSING FATALLY DIES
        "errors": errors,
        "warnings": warnings,
        "node_count": len(wf.nodes),
        "edge_count": len(wf.connections),
        "entry_nodes": [n.id for n in wf.nodes if n.id not in targets],
        "terminal_nodes": terminal_nodes,
    }


def _has_cycle(node_ids: list[str], adjacency: dict[str, list[str]]) -> bool:
    """DFS-based cycle detection."""
    visited: set[str] = set()
    active: set[str] = set()
    cycle_found = False

    def dfs(node_id: str) -> None:
        nonlocal cycle_found
        if node_id in active:
            cycle_found = True
            return
        if node_id in visited or cycle_found:
            return
        visited.add(node_id)
        active.add(node_id)
        for neighbor in adjacency.get(node_id, []):
            dfs(neighbor)
        active.remove(node_id)

    for nid in node_ids:
        if nid not in visited:
            dfs(nid)
    return cycle_found
