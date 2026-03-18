"""
Skill service — business logic for the Skills Library and Visual Skill Designer.
"""
from typing import Any, Dict, List, Tuple
from sqlalchemy.orm import Session
from app.common.errors import (skill_name_exists, skill_key_exists,
                               skill_version_not_found, skill_version_not_draft,
                               skill_version_not_compiled, skill_graph_validation_failed)
from app.common.utils import (generate_unique_id, compute_sha256_hash,
                              deserialise_json, serialise_json)
from app.skill import repository as skill_repository
from app.models.skill import (RunSkillResponse, SaveSkillGraphRequest,
                               SkillGraphConnection, SkillGraphResponse)
from app.logger.logging import logger


# =========================================================================
# Skill Metadata CRUD
# =========================================================================

def list_all_skills(
    db: Session,
    client_id: str | None = None,
    status: str | None = None,
    search_query: str | None = None,
) -> Dict:
    items = skill_repository.fetch_all_skills(db, client_id=client_id, status=status, search_query=search_query)
    return {"items": items, "total": len(items)}


def create_skill(db: Session, request, user_id: str = "1") -> Dict:
    """Create a new Skill with an initial draft version and starter graph."""
    if skill_repository.does_skill_name_exist(db, request.client_id, request.name):
        skill_name_exists()

    skill_key = request.skill_key or generate_unique_id("SK")[:8].upper()
    if skill_repository.does_skill_key_exist(db, request.client_id, skill_key):
        skill_key_exists()

    skill_id = generate_unique_id("skill_")
    skill_version_id = generate_unique_id("sv_")

    skill_repository.insert_skill(
        db, skill_id=skill_id, client_id=request.client_id,
        name=request.name, skill_key=skill_key, description=request.description,
        category_id=request.category_id, capability_id=request.capability_id, created_by=user_id,
    )
    skill_repository.insert_skill_version(
        db, skill_version_id=skill_version_id, skill_id=skill_id,
        environment=request.environment, created_by=user_id,
    )

    if request.start_from.mode == "blank":
        skill_repository.create_blank_graph(db, skill_version_id)
    elif request.start_from.mode == "clone" and request.start_from.clone:
        skill_repository.clone_graph(db, new_skill_version_id=skill_version_id,
                                    source_skill_version_id=request.start_from.clone.source_skill_version_id)

    if request.tags:
        tag_ids = skill_repository.upsert_tags(db, request.tags)
        skill_repository.attach_tags_to_skill(db, skill_id, tag_ids)

    logger.debug(f"Created skill '{request.name}' (key={skill_key}, id={skill_id})")

    return {
        "skill_id": skill_id,
        "skill_version_id": skill_version_id,
    }


def get_skill(db: Session, skill_id: str) -> dict | None:
    """Fetch a single skill's full metadata."""
    return skill_repository.fetch_skill_by_id(db, skill_id)


def update_skill(db: Session, skill_id: str, request) -> bool:
    """Update skill metadata and optionally tags."""
    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        return False

    success = skill_repository.update_skill(db, skill_id, update_data)

    if "tags" in update_data:
        skill_repository.remove_all_tags_from_skill(db, skill_id)
        if update_data["tags"]:
            tag_ids = skill_repository.upsert_tags(db, update_data["tags"])
            skill_repository.attach_tags_to_skill(db, skill_id, tag_ids)

    if success:
        logger.debug(f"Updated skill '{skill_id}'")
    return success


def delete_skill(db: Session, skill_id: str) -> bool:
    """Delete a skill and all its versions."""
    success = skill_repository.delete_skill(db, skill_id)
    if success:
        logger.debug(f"Deleted skill '{skill_id}'")
    return success


# =========================================================================
# Skill Graph / Designer
# =========================================================================

def get_skill_graph(db: Session, skill_version_id: str) -> SkillGraphResponse:
    """Load the graph (nodes + connections) for a skill version."""
    return skill_repository.fetch_skill_graph(db, skill_version_id)


def save_graph(db: Session, skill_version_id: str, request: SaveSkillGraphRequest) -> SkillGraphResponse:
    """Bulk-save the entire graph (nodes + connections) for a skill version."""
    skill_repository.save_skill_graph(db, skill_version_id, request.nodes, request.connections)
    logger.debug(f"Saved graph for skill version {skill_version_id} "
                f"({len(request.nodes)} nodes, {len(request.connections)} connections)")
    return skill_repository.fetch_skill_graph(db, skill_version_id)


def update_node(db: Session, skill_version_id: str, node_id: str, data: dict) -> dict:
    """Update a single node's configuration data."""
    skill_repository.update_node_data(db, skill_version_id, node_id, data)
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
        import collections
        adj = collections.defaultdict(list)
        for conn in graph.connections.values():
            adj[conn.source].append(conn.target)
        
        visited, stack = set(), [triggers[0].id]
        while stack:
            cur = stack.pop()
            if cur in visited: continue
            visited.add(cur)
            for nb in adj.get(cur, []):
                if nb not in visited: stack.append(nb)
        
        unreachable = [nid for nid in node_ids if nid not in visited]
        if unreachable:
            warnings.append(f"Unreachable nodes: {', '.join(unreachable)}")

    return errors, warnings


def validate_graph(db: Session, skill_version_id: str) -> dict:
    graph = skill_repository.fetch_skill_graph(db, skill_version_id)
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
    graph = skill_repository.fetch_skill_graph(db, skill_version_id)
    errors, _ = _validate_skill_graph(graph)
    if errors:
        skill_graph_validation_failed(errors)
    compiled = _compile_graph_to_langgraph_json(graph)
    compiled_text = serialise_json(compiled)
    compile_hash = compute_sha256_hash(compiled_text)
    skill_repository.save_compiled_output(db, skill_version_id, compiled_text, compile_hash)
    logger.debug(f"Compiled skill version {skill_version_id} (hash={compile_hash[:12]})")
    return {"compile_hash": compile_hash, "compiled_skill_json": compiled}


# =========================================================================
# Publish
# =========================================================================

def publish_skill_version(db: Session, skill_version_id: str, publish_notes: str = None) -> dict:
    version_row = skill_repository.fetch_skill_version_by_id(db, skill_version_id)
    if not version_row:
        skill_version_not_found()
    if version_row["status"] != "draft":
        skill_version_not_draft()
    if not version_row["compiled_skill_json"]:
        skill_version_not_compiled()
    
    published_at = skill_repository.publish_skill_version(
        db, skill_version_id, version_row["skill_id"], version_row["environment"], publish_notes)
    
    logger.debug(f"Published skill version {skill_version_id} at {published_at}")
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

    import collections
    out_edges = collections.defaultdict(list)
    for e in edges:
        out_edges[e["source"]].append(e)

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
            if not e.get("is_default") and _evaluate_route_condition(e.get("condition", {}), ctx, last_out):
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
    from sqlalchemy import text
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
