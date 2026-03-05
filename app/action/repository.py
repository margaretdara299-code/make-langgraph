"""
Action repository — database queries for the Action Catalog.
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.common.errors import action_key_exists
from app.common.utils import deserialise_json, generate_unique_id, generate_utc_timestamp


def parse_schema_fields(schema_json: dict) -> list:
    if not schema_json:
        return []
    if isinstance(schema_json.get("fields"), list):
        return [{"name": f["name"], "type": f.get("type", "string"), "required": bool(f.get("required", False))}
                for f in schema_json["fields"] if isinstance(f, dict) and f.get("name")]
    return [{"name": k, "type": v.get("type", "string"), "required": bool(v.get("required", False))}
            for k, v in schema_json.items() if isinstance(v, dict)]


def fetch_all_actions(db: Session, status: Optional[str] = None, capability: Optional[str] = None,
                      category: Optional[str] = None, search_query: Optional[str] = None) -> list:
    where_clauses = ["1=1"]
    params = {}
    if status:
        where_clauses.append("action_version.status=:status")
        params["status"] = status
    if capability:
        where_clauses.append("action_definition.capability=:capability")
        params["capability"] = capability.upper()
    if category:
        where_clauses.append("action_definition.category=:category")
        params["category"] = category
    if search_query:
        where_clauses.append("(action_definition.name LIKE :search OR action_definition.action_key LIKE :search)")
        params["search"] = f"%{search_query}%"

    rows = db.execute(text(f"""
        SELECT action_definition.*, action_version.action_version_id,
               action_version.version, action_version.status AS version_status, action_version.is_active
        FROM action_definition
        LEFT JOIN action_version ON action_version.action_definition_id = action_definition.action_definition_id AND action_version.is_active = 1
        WHERE {" AND ".join(where_clauses)}
        ORDER BY action_definition.updated_at DESC"""), params).mappings().all()
    return [dict(row) for row in rows]


def insert_action_definition(db: Session, request, user_id: str) -> dict:
    action_definition_id = generate_unique_id("ad_")
    action_version_id = generate_unique_id("av_")
    timestamp = generate_utc_timestamp()
    try:
        db.execute(text("""INSERT INTO action_definition
               (action_definition_id, action_key, name, description, category, capability, icon,
                default_node_title, scope, client_id, status, created_by, created_at, updated_at)
               VALUES (:id, :key, :name, :desc, :cat, :cap, :icon, :title, :scope, :client, 'active', :user, :ts, :ts)"""),
            {"id": action_definition_id, "key": request.action_key, "name": request.name,
             "desc": request.description, "cat": request.category, "cap": request.capability,
             "icon": request.icon, "title": request.default_node_title, "scope": request.scope,
             "client": request.client_id, "user": user_id, "ts": timestamp})
    except IntegrityError:
        action_key_exists()

    db.execute(text("""INSERT INTO action_version
           (action_version_id, action_definition_id, version, status, is_active, created_by, created_at)
           VALUES (:id, :ad_id, '0.1.0', 'draft', 0, :user, :ts)"""),
        {"id": action_version_id, "ad_id": action_definition_id, "user": user_id, "ts": timestamp})

    return {
        "action_definition": {"id": action_definition_id, "action_key": request.action_key, "name": request.name},
        "draft_version": {"id": action_version_id, "version": "0.1.0", "status": "draft"},
    }


# =========================================================================
# Designer Actions — with environment + policy_json filtering
# =========================================================================
def fetch_designer_actions(db: Session, client_id: str, environment: str = "dev",
                           capability: Optional[str] = None, category: Optional[str] = None,
                           search_query: Optional[str] = None) -> list:
    """Return published actions for the Designer left-rail, filtered by environment policy."""
    where_clauses = [
        "action_version.status = 'published'",
        "action_version.is_active = 1",
        "action_definition.status IN ('active', 'deprecated')",
        "(action_definition.scope = 'global' OR (action_definition.scope = 'client' AND action_definition.client_id = :client_id))",
    ]
    params = {"client_id": client_id}

    if capability:
        where_clauses.append("action_definition.capability=:capability")
        params["capability"] = capability.upper()
    if category:
        where_clauses.append("action_definition.category=:category")
        params["category"] = category
    if search_query:
        where_clauses.append("(action_definition.name LIKE :search OR action_definition.action_key LIKE :search)")
        params["search"] = f"%{search_query}%"

    rows = db.execute(text(f"""
        SELECT action_definition.action_key, action_definition.name, action_definition.category,
               action_definition.capability, action_definition.icon, action_definition.default_node_title,
               action_version.action_version_id, action_version.inputs_schema_json,
               action_version.outputs_schema_json, action_version.execution_json,
               action_version.policy_json
        FROM action_definition
        JOIN action_version ON action_version.action_definition_id = action_definition.action_definition_id
        WHERE {" AND ".join(where_clauses)}
        ORDER BY action_definition.category, action_definition.name"""),
        params).mappings().all()

    # Filter by environment_availability in policy_json
    result = []
    for r in rows:
        policy = deserialise_json(r["policy_json"], {})
        env_availability = policy.get("environment_availability")
        if env_availability is not None:
            if not env_availability.get(environment, False):
                continue

        execution_config = deserialise_json(r["execution_json"], {})
        result.append({
            "action_version_id": r["action_version_id"],
            "action_key": r["action_key"],
            "name": r["name"],
            "category": r["category"],
            "capability": r["capability"],
            "icon": r["icon"],
            "default_node_title": r["default_node_title"],
            "requires_connector_type": execution_config.get("connector_type") if r["capability"] == "API" else None,
            "inputs": parse_schema_fields(deserialise_json(r["inputs_schema_json"], {})),
            "outputs": parse_schema_fields(deserialise_json(r["outputs_schema_json"], {})),
        })
    return result
