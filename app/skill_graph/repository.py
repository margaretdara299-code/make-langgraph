"""
Skill graph repository — HYBRID storage model.

Nodes:  stored as JSON in skill_version.nodes
Edges:  stored in skill_route table (source of truth)
"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.common.errors import skill_version_not_found, skill_version_not_draft
from app.common.response import raise_bad_request, raise_not_found
from app.common.utils import deserialise_json, generate_unique_id, generate_utc_timestamp, serialise_json
from app.models.skill import SkillGraphConnection, SkillGraphNode, SkillGraphResponse


# =========================================================================
# Create / Clone
# =========================================================================
def create_blank_graph(db: Session, skill_version_id: str) -> None:
    """Write a minimal starter graph: trigger → end node, plus one edge in skill_route."""
    nodes_json = serialise_json([
        {"id": "start", "type": "trigger.queue", "position": {"x": 120, "y": 160},
         "data": {"label": "Start", "description": "Entry trigger"}},
        {"id": "end", "type": "end.success", "position": {"x": 520, "y": 160},
         "data": {"label": "End", "description": "Terminal node"}},
    ])
    db.execute(
        text("UPDATE skill_version SET nodes=:nodes WHERE skill_version_id=:sv_id"),
        {"nodes": nodes_json, "sv_id": skill_version_id},
    )
    edge_id = generate_unique_id("edge_")
    db.execute(
        text("""INSERT INTO skill_route
           (skill_route_id, skill_version_id, from_node_key, to_node_key,
            condition_json, is_default)
           VALUES (:id, :sv_id, :from_key, :to_key, :cond, :default)"""),
        {"id": edge_id, "sv_id": skill_version_id,
         "from_key": "start", "to_key": "end",
         "cond": serialise_json({}), "default": 1},
    )


def clone_graph(db: Session, new_skill_version_id: str, source_skill_version_id: str) -> None:
    """Copy nodes JSON + skill_route rows from source to new version."""
    source = db.execute(
        text("SELECT nodes FROM skill_version WHERE skill_version_id=:sv_id"),
        {"sv_id": source_skill_version_id},
    ).mappings().first()
    if not source:
        return
    db.execute(
        text("UPDATE skill_version SET nodes=:nodes WHERE skill_version_id=:sv_id"),
        {"nodes": source["nodes"], "sv_id": new_skill_version_id},
    )
    source_routes = db.execute(
        text("SELECT from_node_key, to_node_key, from_handle, to_handle, condition_json, is_default "
             "FROM skill_route WHERE skill_version_id=:sv_id"),
        {"sv_id": source_skill_version_id},
    ).mappings().all()
    for r in source_routes:
        db.execute(
            text("""INSERT INTO skill_route
               (skill_route_id, skill_version_id, from_node_key, to_node_key,
                from_handle, to_handle, condition_json, is_default)
               VALUES (:id, :sv_id, :from_key, :to_key, :from_h, :to_h, :cond, :default)"""),
            {"id": generate_unique_id("edge_"), "sv_id": new_skill_version_id,
             "from_key": r["from_node_key"], "to_key": r["to_node_key"],
             "from_h": r["from_handle"], "to_h": r["to_handle"],
             "cond": r["condition_json"], "default": r["is_default"]},
        )


# =========================================================================
# Load graph — nodes from JSON, edges from skill_route
# =========================================================================
def load_skill_graph(db: Session, skill_version_id: str) -> SkillGraphResponse:
    version_row = db.execute(
        text("SELECT skill_version.*, skill.skill_id AS _skill_id "
             "FROM skill_version JOIN skill ON skill.skill_id = skill_version.skill_id "
             "WHERE skill_version.skill_version_id=:sv_id"),
        {"sv_id": skill_version_id},
    ).mappings().first()
    if not version_row:
        skill_version_not_found()

    # Parse nodes from JSON
    nodes = [SkillGraphNode(**n) for n in deserialise_json(version_row["nodes"] or "[]", [])]

    # Read edges from skill_route
    route_rows = db.execute(
        text("SELECT skill_route_id, from_node_key, to_node_key, from_handle, to_handle, "
             "condition_json, is_default FROM skill_route "
             "WHERE skill_version_id=:sv_id ORDER BY created_at ASC"),
        {"sv_id": skill_version_id},
    ).mappings().all()

    connections: Dict[str, SkillGraphConnection] = {}
    for r in route_rows:
        edge_id = r["skill_route_id"]
        connections[edge_id] = SkillGraphConnection(
            id=edge_id,
            source=r["from_node_key"],
            target=r["to_node_key"],
            sourceHandle=r["from_handle"],
            targetHandle=r["to_handle"],
            condition=deserialise_json(r["condition_json"], {}),
            is_default=bool(r["is_default"]),
        )

    return SkillGraphResponse(
        skill_version_id=version_row["skill_version_id"],
        skill_id=version_row["_skill_id"],
        environment=version_row["environment"],
        version=version_row["version"],
        status=version_row["status"],
        nodes=nodes,
        connections=connections,
    )


# =========================================================================
# Save graph — nodes to JSON, edges to skill_route
# =========================================================================
def save_graph(db: Session, skill_version_id: str,
               nodes: List[SkillGraphNode],
               connections: Dict[str, SkillGraphConnection]) -> None:
    """Persist the full canvas: nodes into skill_version.nodes, edges into skill_route."""
    version_row = db.execute(
        text("SELECT status FROM skill_version WHERE skill_version_id=:sv_id"),
        {"sv_id": skill_version_id},
    ).mappings().first()
    if not version_row:
        skill_version_not_found()
    if version_row["status"] != "draft":
        skill_version_not_draft()

    # Validate unique node ids
    node_ids = [n.id for n in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise_bad_request("Duplicate node ids detected")

    node_id_set = set(node_ids)

    # Validate all connection source/target reference existing nodes
    for edge_id, conn in connections.items():
        if conn.source not in node_id_set:
            raise_bad_request(f"Connection '{edge_id}' source '{conn.source}' not found in nodes")
        if conn.target not in node_id_set:
            raise_bad_request(f"Connection '{edge_id}' target '{conn.target}' not found in nodes")

    # 1. Save nodes as JSON
    nodes_json = serialise_json([n.model_dump() for n in nodes])
    db.execute(
        text("UPDATE skill_version SET nodes=:nodes WHERE skill_version_id=:sv_id"),
        {"nodes": nodes_json, "sv_id": skill_version_id},
    )

    # 2. Sync edges into skill_route (upsert + delete stale)
    incoming_edge_ids = set(connections.keys())
    existing_edge_ids = {
        row["skill_route_id"] for row in db.execute(
            text("SELECT skill_route_id FROM skill_route WHERE skill_version_id=:sv_id"),
            {"sv_id": skill_version_id},
        ).mappings().all()
    }

    stale_ids = existing_edge_ids - incoming_edge_ids
    for stale_id in stale_ids:
        db.execute(
            text("DELETE FROM skill_route WHERE skill_route_id=:id"),
            {"id": stale_id},
        )

    for edge_id, conn in connections.items():
        db.execute(
            text("""INSERT INTO skill_route
               (skill_route_id, skill_version_id, from_node_key, to_node_key,
                from_handle, to_handle, condition_json, is_default)
               VALUES (:id, :sv_id, :from_key, :to_key, :from_h, :to_h, :cond, :default)
               ON CONFLICT(skill_route_id) DO UPDATE SET
                 from_node_key=excluded.from_node_key, to_node_key=excluded.to_node_key,
                 from_handle=excluded.from_handle, to_handle=excluded.to_handle,
                 condition_json=excluded.condition_json, is_default=excluded.is_default"""),
            {"id": edge_id, "sv_id": skill_version_id,
             "from_key": conn.source, "to_key": conn.target,
             "from_h": conn.sourceHandle, "to_h": conn.targetHandle,
             "cond": serialise_json(conn.condition or {}),
             "default": 1 if conn.is_default else 0},
        )


# =========================================================================
# Node data update
# =========================================================================
def update_node_data(db: Session, skill_version_id: str, node_id: str, data: dict) -> None:
    row = db.execute(
        text("SELECT nodes FROM skill_version WHERE skill_version_id=:sv_id"),
        {"sv_id": skill_version_id},
    ).mappings().first()
    if not row:
        skill_version_not_found()

    items = deserialise_json(row["nodes"], [])
    found = False
    for node in items:
        if node.get("id") == node_id:
            node["data"] = data
            found = True
            break
    if not found:
        raise_not_found(f"Node '{node_id}' not found in graph")

    db.execute(
        text("UPDATE skill_version SET nodes=:nodes WHERE skill_version_id=:sv_id"),
        {"nodes": serialise_json(items), "sv_id": skill_version_id},
    )


# =========================================================================
# Version lifecycle helpers
# =========================================================================
def fetch_skill_version(db: Session, skill_version_id: str):
    return db.execute(
        text("SELECT * FROM skill_version WHERE skill_version_id=:sv_id"),
        {"sv_id": skill_version_id},
    ).mappings().first()


def save_compiled_output(db: Session, skill_version_id: str, compiled_json_text: str, compile_hash: str) -> None:
    db.execute(
        text("UPDATE skill_version SET compiled_skill_json=:json, compile_hash=:hash "
             "WHERE skill_version_id=:sv_id"),
        {"json": compiled_json_text, "hash": compile_hash, "sv_id": skill_version_id},
    )


def publish_skill_version(db: Session, skill_version_id: str, skill_id: str,
                           environment: str, publish_notes: Optional[str]) -> str:
    timestamp = generate_utc_timestamp()
    db.execute(
        text("UPDATE skill_version SET is_active=0 WHERE skill_id=:skill_id AND environment=:env "
             "AND status='published' AND is_active=1"),
        {"skill_id": skill_id, "env": environment},
    )
    db.execute(
        text("UPDATE skill_version SET status='published', is_active=1, published_at=:ts, "
             "notes=:notes WHERE skill_version_id=:sv_id"),
        {"ts": timestamp, "notes": publish_notes, "sv_id": skill_version_id},
    )
    return timestamp
