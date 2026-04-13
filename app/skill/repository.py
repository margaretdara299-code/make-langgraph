"""
Skill repository — database queries for skill metadata, tags, listing, and graph lifecycle.
"""
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.common.utils import generate_unique_id, generate_utc_timestamp, serialize_to_json, deserialize_json
from app.skill.models import SkillGraphNode, SkillGraphConnection, SkillGraphResponse
from app.common.errors import skill_version_not_found, skill_version_not_draft
from app.common.response import raise_bad_request, raise_not_found


# =========================================================================
# Metadata & Tags Helpers
# =========================================================================

def does_skill_name_exist(db: Session, client_id: int, name: str) -> bool:
    row = db.execute(
        text("SELECT 1 FROM skill WHERE client_id=:client_id AND name=:name LIMIT 1"),
        {"client_id": client_id, "name": name},
    ).mappings().first()
    return row is not None


def does_skill_key_exist(db: Session, client_id: int, skill_key: str) -> bool:
    row = db.execute(
        text("SELECT 1 FROM skill WHERE client_id=:client_id AND skill_key=:skill_key LIMIT 1"),
        {"client_id": client_id, "skill_key": skill_key},
    ).mappings().first()
    return row is not None


def upsert_tags(db: Session, tag_names: List[str]) -> List[int]:
    """Insert tags if they do not exist. Returns a list of tag IDs."""
    tag_ids = []
    for tag_name in tag_names:
        existing_row = db.execute(
            text("SELECT tag_id FROM tag WHERE name=:name"), {"name": tag_name}
        ).mappings().first()
        if existing_row:
            tag_ids.append(existing_row["tag_id"])
        else:
            res = db.execute(
                text("INSERT INTO tag (name) VALUES (:name)"),
                {"name": tag_name},
            )
            tag_ids.append(res.lastrowid)
    return tag_ids


def attach_tags_to_skill(db: Session, skill_id: int, tag_ids: List[int]) -> None:
    for tag_id in tag_ids:
        db.execute(
            text("INSERT OR IGNORE INTO skill_tag (skill_id, tag_id) VALUES (:skill_id, :tag_id)"),
            {"skill_id": skill_id, "tag_id": tag_id},
        )


def remove_all_tags_from_skill(db: Session, skill_id: int) -> None:
    """Clear all tags for a skill."""
    db.execute(
        text("DELETE FROM skill_tag WHERE skill_id = :skill_id"),
        {"skill_id": skill_id}
    )


# =========================================================================
# Skill CRUD
# =========================================================================

def insert_skill(
    db: Session,
    client_id: int,
    name: str, skill_key: str, description: str | None,
    category_id: int | None, capability_id: int | None, is_active: int = 1, created_by: int = 1,
) -> int:
    timestamp = generate_utc_timestamp()
    res = db.execute(
        text("""INSERT INTO skill
           (client_id, name, skill_key, description,
            category_id, capability_id, is_active,
            created_by, created_at, updated_at)
           VALUES (:client_id, :name, :skill_key, :description,
                   :category_id, :capability_id, :is_active,
                   :created_by, :created_at, :updated_at)"""),
        {
            "client_id": client_id,
            "name": name, "skill_key": skill_key, "description": description,
            "category_id": category_id, "capability_id": capability_id, "is_active": is_active,
            "created_by": created_by, "created_at": timestamp, "updated_at": timestamp,
        },
    )
    return res.lastrowid


def fetch_all_skills(
    db: Session,
    client_id: int | None = None,
    status: str | None = None,
    search_query: str | None = None,
) -> list:
    """Fetch skills with their latest active version, tags, and node counts."""
    where_clauses = ["1=1"]
    params = {}

    if client_id:
        where_clauses.append("skill.client_id=:client_id")
        params["client_id"] = client_id
    if status:
        where_clauses.append("skill_version.status=:status")
        params["status"] = status
    if search_query:
        where_clauses.append("(skill.name LIKE :search OR skill.skill_key LIKE :search OR skill.description LIKE :search)")
        params["search"] = f"%{search_query}%"

    skill_rows = db.execute(
        text(f"""
        SELECT skill.*,
               skill_version.skill_version_id AS latest_version_id,
               skill_version.version,
               skill_version.status AS version_status,
               skill_version.environment
        FROM skill
        LEFT JOIN skill_version
          ON skill_version.skill_id = skill.skill_id AND skill_version.is_active = 1
        WHERE {" AND ".join(where_clauses)}
        ORDER BY skill.updated_at DESC
        """),
        params,
    ).mappings().all()

    result_items = []
    for skill_row in skill_rows:
        associated_tags = [
            tag_row["name"]
            for tag_row in db.execute(
                text("""SELECT tag.name FROM tag
                   JOIN skill_tag ON skill_tag.tag_id = tag.tag_id
                   WHERE skill_tag.skill_id=:skill_id"""),
                {"skill_id": skill_row["skill_id"]},
            ).mappings().all()
        ]

        result_items.append({
            "id": skill_row["skill_id"],
            "client_id": skill_row["client_id"],
            "name": skill_row["name"],
            "skill_key": skill_row["skill_key"],
            "description": skill_row["description"],
            "category_id": skill_row["category_id"],
            "capability_id": skill_row["capability_id"],
            "is_active": skill_row["is_active"],
            "tags": associated_tags,
            "latest_version_id": skill_row["latest_version_id"],
            "version": skill_row["version"],
            "status": skill_row["version_status"],
            "environment": skill_row["environment"],
            "updated_at": skill_row["updated_at"],
        })
    return result_items


def fetch_skill_by_id(db: Session, skill_id: int) -> dict | None:
    """Fetch a single skill with its latest active version and tags."""
    skill_row = db.execute(
        text("""
        SELECT skill.*,
               skill_version.skill_version_id AS latest_version_id,
               skill_version.version,
               skill_version.status AS version_status,
               skill_version.environment
        FROM skill
        LEFT JOIN skill_version
          ON skill_version.skill_id = skill.skill_id AND skill_version.is_active = 1
        WHERE skill.skill_id = :skill_id
        LIMIT 1
        """),
        {"skill_id": skill_id},
    ).mappings().first()

    if not skill_row:
        return None

    associated_tags = [
        tag_row["name"]
        for tag_row in db.execute(
            text("""SELECT tag.name FROM tag
               JOIN skill_tag ON skill_tag.tag_id = tag.tag_id
               WHERE skill_tag.skill_id=:skill_id"""),
            {"skill_id": skill_id},
        ).mappings().all()
    ]

    return {
        "id": skill_row["skill_id"],
        "client_id": skill_row["client_id"],
        "name": skill_row["name"],
        "skill_key": skill_row["skill_key"],
        "description": skill_row["description"],
        "category_id": skill_row["category_id"],
        "capability_id": skill_row["capability_id"],
        "is_active": skill_row["is_active"],
        "tags": associated_tags,
        "latest_version_id": skill_row["latest_version_id"],
        "version": skill_row["version"],
        "status": skill_row["version_status"],
        "environment": skill_row["environment"],
        "created_at": skill_row["created_at"],
        "updated_at": skill_row["updated_at"],
    }


def update_skill(db: Session, skill_id: int, update_data: dict) -> bool:
    """Update skill metadata in the database."""
    if not update_data:
        return False

    set_clauses = []
    params = {"skill_id": skill_id, "ts": generate_utc_timestamp()}

    for key, value in update_data.items():
        if key == "tags":
            continue
        set_clauses.append(f"{key} = :{key}")
        params[key] = 1 if key == "is_active" and isinstance(value, bool) else value

    if not set_clauses and "tags" not in update_data:
        return False

    if set_clauses:
        set_clauses.append("updated_at = :ts")
        query = f"UPDATE skill SET {', '.join(set_clauses)} WHERE skill_id = :skill_id"
        db.execute(text(query), params)

    return True


def delete_skill(db: Session, skill_id: int) -> bool:
    """Delete a skill and all associated data (versions, routes)."""
    # Foreign keys ON DELETE CASCADE handle skill_version and skill_route
    result = db.execute(
        text("DELETE FROM skill WHERE skill_id = :skill_id"),
        {"skill_id": skill_id}
    )
    return result.rowcount > 0


# =========================================================================
# Skill Version Lifecycle
# =========================================================================

def insert_skill_version(
    db: Session,
    skill_id: int,
    environment: str, created_by: int = 1, version: str = "1.0.1",
) -> int:
    res = db.execute(
        text("""INSERT INTO skill_version
           (skill_id, environment, version, status, is_active, created_by, created_at)
           VALUES (:skill_id, :environment, :version, 'draft', 1, :created_by, :created_at)"""),
        {
            "skill_id": skill_id,
            "environment": environment, "version": version,
            "created_by": created_by, "created_at": generate_utc_timestamp(),
        },
    )
    return res.lastrowid


def fetch_skill_version_by_id(db: Session, skill_version_id: int) -> dict | None:
    """Return a single skill_version row."""
    row = db.execute(
        text("SELECT * FROM skill_version WHERE skill_version_id = :id"),
        {"id": skill_version_id}
    ).mappings().first()
    return dict(row) if row else None
def publish_skill_version(db: Session, skill_version_id: int, skill_id: int,
                           environment: str, publish_notes: str | None) -> str:
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


def unpublish_skill_version(db: Session, skill_version_id: int) -> None:
    """Reset a published version back to unpublished status."""
    db.execute(
        text("UPDATE skill_version SET status='unpublished', published_at=NULL, is_active=1 "
             "WHERE skill_version_id=:sv_id"),
        {"sv_id": skill_version_id},
    )


# =========================================================================
# Graph Lifecycle (Hybrid Model: Nodes in JSON, Edges in skill_route)
# =========================================================================

def create_blank_graph(db: Session, skill_version_id: int) -> None:
    """Write an empty graph to allow the user to build from scratch natively in the UI."""
    db.execute(
        text("UPDATE skill_version SET nodes=:nodes, connections=:connections WHERE skill_version_id=:sv_id"),
        {"nodes": "[]", "connections": "{}", "sv_id": skill_version_id},
    )


def clone_graph(db: Session, new_skill_version_id: int, source_skill_version_id: int) -> None:
    """Copy nodes and connections JSON from source to new version. (skill_route is deprecated)."""
    source = db.execute(
        text("SELECT nodes, connections FROM skill_version WHERE skill_version_id=:sv_id"),
        {"sv_id": source_skill_version_id},
    ).mappings().first()
    if not source:
        return
    db.execute(
        text("UPDATE skill_version SET nodes=:nodes, connections=:connections WHERE skill_version_id=:sv_id"),
        {"nodes": source["nodes"], "connections": source["connections"], "sv_id": new_skill_version_id},
    )


def fetch_skill_graph(db: Session, skill_version_id: int) -> SkillGraphResponse:
    """Load the graph (nodes + connections) for a skill version."""
    version_row = db.execute(
        text("SELECT skill_version.*, skill.skill_id AS _skill_id, "
             "skill.name AS skill_name, skill.skill_key, skill.description "
             "FROM skill_version JOIN skill ON skill.skill_id = skill_version.skill_id "
             "WHERE skill_version.skill_version_id=:sv_id"),
        {"sv_id": skill_version_id},
    ).mappings().first()
    if not version_row:
        skill_version_not_found()

    # Read nodes and connections from their respective columns
    raw_nodes_col = deserialize_json(version_row["nodes"] or "[]", [])
    raw_connections_col = deserialize_json(version_row["connections"] or "{}", {})
    raw_viewport_col = deserialize_json(version_row.get("viewport_json", "{}") or "{}", {})
    
    if isinstance(raw_nodes_col, dict) and "nodes" in raw_nodes_col:
        # Fallback for composite format if it exists in the nodes column
        nodes_data = raw_nodes_col.get("nodes", [])
        connections_data = raw_nodes_col.get("connections", {})
    else:
        # New separate column format
        nodes_data = raw_nodes_col if isinstance(raw_nodes_col, list) else []
        connections_data = raw_connections_col if isinstance(raw_connections_col, dict) else {}

    nodes = [SkillGraphNode(**n) for n in nodes_data]
    
    connections: dict = {}
    for edge_id, conn_dict in connections_data.items():
        connections[edge_id] = SkillGraphConnection(**conn_dict)

    viewport_data = raw_viewport_col if isinstance(raw_viewport_col, dict) else {}

    return SkillGraphResponse(
        skill_version_id=version_row["skill_version_id"],
        skill_id=version_row["_skill_id"],
        name=version_row.get("skill_name"),
        skill_key=version_row.get("skill_key"),
        description=version_row.get("description"),
        environment=version_row["environment"],
        version=version_row["version"],
        status=version_row["status"],
        nodes=nodes,
        connections=connections,
        viewport_json=viewport_data,
    )


def save_skill_graph(db: Session, skill_version_id: int, nodes: list, connections: dict, viewport_json: dict) -> None:
    """Persist the full canvas: both nodes, connections, and viewport into skill_version."""
    version_row = db.execute(
        text("SELECT status FROM skill_version WHERE skill_version_id=:sv_id"),
        {"sv_id": skill_version_id},
    ).mappings().first()
    if not version_row:
        skill_version_not_found()

    # 1. Save nodes, connections, and viewport into their respective columns
    nodes_serialisable = [
        n.model_dump() if hasattr(n, "model_dump") else n
        for n in nodes
    ]
    connections_serialisable = {
        k: (v.model_dump() if hasattr(v, "model_dump") else v)
        for k, v in connections.items()
    }
    viewport_serialisable = viewport_json
    
    nodes_json = serialize_to_json(nodes_serialisable)
    connections_json_str = serialize_to_json(connections_serialisable)
    viewport_json_str = serialize_to_json(viewport_serialisable)
    
    db.execute(
        text("UPDATE skill_version SET nodes=:nodes, connections=:connections, viewport_json=:viewport WHERE skill_version_id=:sv_id"),
        {"nodes": nodes_json, "connections": connections_json_str, "viewport": viewport_json_str, "sv_id": skill_version_id},
    )

    # 3. Bump updated_at
    db.execute(
        text("""UPDATE skill SET updated_at = :ts
                WHERE skill_id = (SELECT skill_id FROM skill_version WHERE skill_version_id = :sv_id)"""),
        {"sv_id": skill_version_id, "ts": generate_utc_timestamp()}
    )


def update_node_data(db: Session, skill_version_id: int, node_id: str, data: dict) -> None:
    """Update a single node's `data` object inside the nodes JSON array."""
    row = db.execute(
        text("SELECT nodes, status FROM skill_version WHERE skill_version_id=:sv_id"),
        {"sv_id": skill_version_id},
    ).mappings().first()
    if not row:
        skill_version_not_found()

    raw_nodes_col = deserialize_json(row["nodes"] or "[]", [])
    
    if isinstance(raw_nodes_col, dict) and "nodes" in raw_nodes_col:
        # Fallback for composite format
        items = raw_nodes_col.get("nodes", [])
    else:
        # New separate format
        items = raw_nodes_col if isinstance(raw_nodes_col, list) else []

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
        {"nodes": serialize_to_json(items), "sv_id": skill_version_id},
    )

    db.execute(
        text("""UPDATE skill SET updated_at = :ts
                WHERE skill_id = (SELECT skill_id FROM skill_version WHERE skill_version_id = :sv_id)"""),
        {"sv_id": skill_version_id, "ts": generate_utc_timestamp()}
    )


def update_compiled_graph(db: Session, skill_version_id: int, compiled_json: str, compile_hash: str) -> None:
    """Save the compiled engine plan back to the skill version record."""
    db.execute(
        text("""UPDATE skill_version 
                SET compiled_skill_json = :json, compile_hash = :hash 
                WHERE skill_version_id = :sv_id"""),
        {"json": compiled_json, "hash": compile_hash, "sv_id": skill_version_id}
    )


