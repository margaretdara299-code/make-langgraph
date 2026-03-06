"""
Skill graph service — business logic for the visual builder and skill lifecycle.
"""
from typing import Any, Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.common.errors import skill_version_not_found, skill_version_not_draft, skill_version_not_compiled, skill_graph_validation_failed
from app.common.response import raise_bad_request
from app.common.utils import compute_sha256_hash, deserialise_json, serialise_json
from app.models.skill import (RunSkillResponse, SaveSkillGraphRequest,
                               SkillGraphConnection, SkillGraphResponse)
from app.skill_graph import repository as graph_repository
from app.logger.logging import logger


def get_graph(db: Session, skill_version_id: str) -> SkillGraphResponse:
    return graph_repository.load_skill_graph(db, skill_version_id)


def save_graph(db: Session, skill_version_id: str, request: SaveSkillGraphRequest) -> SkillGraphResponse:
    graph_repository.save_graph(db, skill_version_id, request.nodes, request.connections)
    logger.info(f"Saved graph for skill version {skill_version_id} "
                f"({len(request.nodes)} nodes, {len(request.connections)} connections)")
    return graph_repository.load_skill_graph(db, skill_version_id)


def update_node_data(db: Session, skill_version_id: str, node_id: str, data: dict) -> dict:
    graph_repository.update_node_data(db, skill_version_id, node_id, data)
    return {"ok": True}


# =========================================================================
# Validate
# =========================================================================
def _validate_skill_graph(graph: SkillGraphResponse) -> Tuple[List[str], List[str]]:
    errors, warnings = [], []
    node_ids = {n.id for n in graph.nodes}

    if not node_ids:
        errors.append("Skill has no nodes.")
        return errors, warnings

    all_ids = [n.id for n in graph.nodes]
    if len(all_ids) != len(set(all_ids)):
        errors.append("Duplicate node ids found.")

    triggers = [n for n in graph.nodes if n.type.startswith("trigger.")]
    if len(triggers) != 1:
        errors.append(f"Skill must have exactly one trigger.* start node; found {len(triggers)}.")
    ends = [n for n in graph.nodes if n.type.startswith("end.")]
    if len(ends) < 1:
        errors.append("Skill must have at least one end.* node.")

    for edge_id, conn in graph.connections.items():
        if conn.source not in node_ids:
            errors.append(f"Connection '{edge_id}': source '{conn.source}' not found in nodes.")
        if conn.target not in node_ids:
            errors.append(f"Connection '{edge_id}': target '{conn.target}' not found in nodes.")

    if triggers:
        adj: Dict[str, List[str]] = {}
        for conn in graph.connections.values():
            adj.setdefault(conn.source, []).append(conn.target)
        visited, stack = set(), [triggers[0].id]
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            for nb in adj.get(cur, []):
                if nb not in visited:
                    stack.append(nb)
        unreachable = [nid for nid in node_ids if nid not in visited]
        if unreachable:
            warnings.append(f"Unreachable nodes: {', '.join(unreachable)}")

    out: Dict[str, list] = {}
    for conn in graph.connections.values():
        out.setdefault(conn.source, []).append(conn)
    for key, conns in out.items():
        if len(conns) > 1 and not any(c.is_default for c in conns):
            warnings.append(f"Node '{key}' has multiple outgoing connections but no default.")

    return errors, warnings


def validate_graph(db: Session, skill_version_id: str) -> dict:
    graph = graph_repository.load_skill_graph(db, skill_version_id)
    errors, warnings = _validate_skill_graph(graph)
    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


# =========================================================================
# Compile
# =========================================================================
def _compile_graph_to_langgraph_json(graph: SkillGraphResponse) -> Dict[str, Any]:
    entry = next((n.id for n in graph.nodes if n.type.startswith("trigger.")), None)

    compiled_nodes = {}
    for node in graph.nodes:
        compiled_nodes[node.id] = {
            "id": node.id,
            "type": node.type,
            "data": node.data,
            "position": node.position,
        }

    compiled_edges = []
    for edge_id, conn in graph.connections.items():
        compiled_edges.append({
            "id": edge_id,
            "source": conn.source,
            "target": conn.target,
            "condition": conn.condition or {},
            "is_default": bool(conn.is_default),
        })

    return {
        "schema_version": "1.0",
        "skill_version_id": graph.skill_version_id,
        "skill_id": graph.skill_id,
        "environment": graph.environment,
        "version": graph.version,
        "entry_node_key": entry,
        "nodes": compiled_nodes,
        "edges": compiled_edges,
    }


def compile_graph(db: Session, skill_version_id: str) -> dict:
    graph = graph_repository.load_skill_graph(db, skill_version_id)
    errors, _ = _validate_skill_graph(graph)
    if errors:
        skill_graph_validation_failed(errors)
    compiled = _compile_graph_to_langgraph_json(graph)
    compiled_text = serialise_json(compiled)
    compile_hash = compute_sha256_hash(compiled_text)
    graph_repository.save_compiled_output(db, skill_version_id, compiled_text, compile_hash)
    logger.info(f"Compiled skill version {skill_version_id} (hash={compile_hash[:12]})")
    return {"compile_hash": compile_hash, "compiled_skill_json": compiled}


# =========================================================================
# Publish
# =========================================================================
def publish_skill_version(db: Session, skill_version_id: str, publish_notes: str = None) -> dict:
    version_row = graph_repository.fetch_skill_version(db, skill_version_id)
    if not version_row:
        skill_version_not_found()
    if version_row["status"] != "draft":
        skill_version_not_draft()
    if not version_row["compiled_skill_json"]:
        skill_version_not_compiled()
    published_at = graph_repository.publish_skill_version(
        db, skill_version_id, version_row["skill_id"], version_row["environment"], publish_notes)
    logger.info(f"Published skill version {skill_version_id} at {published_at}")
    return {"status": "published", "published_at": published_at}


# =========================================================================
# Run
# =========================================================================
def _evaluate_route_condition(condition: dict, context: dict, node_outputs: dict) -> bool:
    if not condition:
        return True
    if condition.get("type") == "expression" and condition.get("language") == "py":
        try:
            return bool(eval(condition.get("expr", ""), {"__builtins__": {}},
                             {"ctx": context, "outputs": node_outputs}))
        except Exception:
            return False
    return False


def _execute_compiled_skill(compiled: dict, input_context: dict, max_steps: int = 200) -> dict:
    ctx = dict(input_context or {})
    nodes = compiled.get("nodes", {})
    edges = compiled.get("edges", [])
    entry = compiled.get("entry_node_key")
    if not entry or entry not in nodes:
        return {"status": "failed", "visited": [], "context": ctx}

    out_edges: Dict[str, list] = {}
    for e in edges:
        out_edges.setdefault(e["source"], []).append(e)

    cur, visited, last_out = entry, [], {}
    for _ in range(max_steps):
        visited.append(cur)
        if str(nodes[cur].get("type", "")).startswith("end."):
            return {"status": "succeeded", "visited": visited, "context": ctx, "last_outputs": last_out}
        candidates = out_edges.get(cur, [])
        if not candidates:
            return {"status": "stopped:no_outgoing_route", "visited": visited, "context": ctx, "last_outputs": last_out}
        nxt = None
        for e in candidates:
            if not e.get("is_default") and _evaluate_route_condition(
                    e.get("condition", {}), ctx, last_out):
                nxt = e["target"]
                break
        if not nxt:
            for e in candidates:
                if e.get("is_default"):
                    nxt = e["target"]
                    break
        if not nxt or nxt not in nodes:
            return {"status": "stopped:no_route_matched", "visited": visited, "context": ctx, "last_outputs": last_out}
        cur = nxt
    return {"status": "failed:max_steps_exceeded", "visited": visited, "context": ctx, "last_outputs": last_out}


def run_skill(db: Session, skill_version_id: str, request) -> dict:
    version_row = db.execute(
        text("SELECT compiled_skill_json FROM skill_version WHERE skill_version_id=:sv_id"),
        {"sv_id": skill_version_id},
    ).mappings().first()
    if not version_row:
        skill_version_not_found()
    compiled = deserialise_json(version_row["compiled_skill_json"], None)
    if not compiled:
        skill_version_not_compiled()
    return _execute_compiled_skill(compiled, request.input_context, request.max_steps)
