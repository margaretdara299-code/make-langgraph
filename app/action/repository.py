"""
Action repository — database queries for the Action Catalog.
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.common.errors import action_key_exists, action_not_found, action_version_not_found, action_version_not_draft
from app.common.utils import deserialise_json, serialise_json, generate_unique_id, generate_utc_timestamp


def parse_schema_fields(schema_json: dict) -> list:
    if not schema_json:
        return []
    if isinstance(schema_json.get("fields"), list):
        return [{"name": f["name"], "type": f.get("type", "string"), "required": bool(f.get("required", False))}
                for f in schema_json["fields"] if isinstance(f, dict) and f.get("name")]
    return [{"name": k, "type": v.get("type", "string"), "required": bool(v.get("required", False))}
            for k, v in schema_json.items() if isinstance(v, dict)]


def fetch_all_actions(db: Session, status: str | None = None, capability: str | None = None,
                      category: str | None = None, search_query: str | None = None) -> list:
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
           (action_version_id, action_definition_id, version, status, is_active,
            inputs_schema_json, execution_json, outputs_schema_json,
            configurations_json, ui_form_json, policy_json,
            created_by, created_at)
           VALUES (:id, :ad_id, '0.1.0', 'draft', 0,
                   :inputs, :execution, :outputs, :configurations, :ui_form, :policy,
                   :user, :ts)"""),
        {"id": action_version_id, "ad_id": action_definition_id, "user": user_id, "ts": timestamp,
         "inputs": serialise_json(request.inputs_schema_json) if request.inputs_schema_json else None,
         "execution": serialise_json(request.execution_json) if request.execution_json else None,
         "outputs": serialise_json(request.outputs_schema_json) if request.outputs_schema_json else None,
         "configurations": serialise_json(request.configurations_json) if request.configurations_json else None,
         "ui_form": serialise_json(request.ui_form_json) if request.ui_form_json else None,
         "policy": serialise_json(request.policy_json) if request.policy_json else None})

    return {
        "action_definition": {"id": action_definition_id, "action_key": request.action_key, "name": request.name},
        "draft_version": {"id": action_version_id, "version": "0.1.0", "status": "draft"},
    }


# =========================================================================
# Designer Actions — with environment + policy_json filtering
# =========================================================================
def fetch_designer_actions(db: Session, client_id: str, environment: str = "dev",
                           capability: str | None = None, category: str | None = None,
                           search_query: str | None = None) -> list:
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


# =========================================================================
# Single Action Fetch (by action_definition_id)
# =========================================================================
def fetch_action_by_id(db: Session, action_definition_id: str) -> dict | None:
    """Return a single action definition with all its versions."""
    row = db.execute(text("""
        SELECT * FROM action_definition
        WHERE action_definition_id = :id"""),
        {"id": action_definition_id}).mappings().first()
    if not row:
        return None

    versions = db.execute(text("""
        SELECT * FROM action_version
        WHERE action_definition_id = :id
        ORDER BY created_at DESC"""),
        {"id": action_definition_id}).mappings().all()

    result = dict(row)
    result["versions"] = []
    for v in versions:
        vd = dict(v)
        vd["inputs_schema_json"] = deserialise_json(vd.get("inputs_schema_json"), {})
        vd["execution_json"] = deserialise_json(vd.get("execution_json"), {})
        vd["outputs_schema_json"] = deserialise_json(vd.get("outputs_schema_json"), {})
        vd["configurations_json"] = deserialise_json(vd.get("configurations_json"), {})
        vd["ui_form_json"] = deserialise_json(vd.get("ui_form_json"), {})
        vd["policy_json"] = deserialise_json(vd.get("policy_json"), {})
        result["versions"].append(vd)
    return result


# =========================================================================
# Update Action Version (draft only)
# =========================================================================
def update_action_version(db: Session, action_version_id: str, request) -> dict:
    """Update JSON schemas on a draft version. Only non-None fields are overwritten."""
    row = db.execute(text("""
        SELECT action_version_id, status FROM action_version
        WHERE action_version_id = :id"""),
        {"id": action_version_id}).mappings().first()
    if not row:
        action_version_not_found()
    if row["status"] != "draft":
        action_version_not_draft()

    set_clauses = []
    params = {"id": action_version_id}

    field_map = {
        "inputs_schema_json": request.inputs_schema_json,
        "execution_json": request.execution_json,
        "outputs_schema_json": request.outputs_schema_json,
        "configurations_json": request.configurations_json,
        "ui_form_json": request.ui_form_json,
        "policy_json": request.policy_json,
    }

    for col, value in field_map.items():
        if value is not None:
            set_clauses.append(f"{col} = :{col}")
            params[col] = serialise_json(value)

    if not set_clauses:
        return {"action_version_id": action_version_id, "message": "No fields to update"}

    db.execute(text(f"""
        UPDATE action_version SET {', '.join(set_clauses)}
        WHERE action_version_id = :id"""), params)

    return {"action_version_id": action_version_id, "updated_fields": list(field_map.keys())}


# =========================================================================
# Publish Action Version
# =========================================================================
def publish_action_version(db: Session, action_version_id: str, release_notes: str | None = None) -> dict:
    """Promote a draft version to published status and mark it as the active version."""
    row = db.execute(text("""
        SELECT av.action_version_id, av.action_definition_id, av.status, av.version
        FROM action_version av
        WHERE av.action_version_id = :id"""),
        {"id": action_version_id}).mappings().first()
    if not row:
        action_version_not_found()
    if row["status"] != "draft":
        action_version_not_draft()

    timestamp = generate_utc_timestamp()
    ad_id = row["action_definition_id"]

    # Deactivate all previous active versions for this action
    db.execute(text("""
        UPDATE action_version SET is_active = 0
        WHERE action_definition_id = :ad_id AND is_active = 1"""),
        {"ad_id": ad_id})

    # Publish and activate this version
    db.execute(text("""
        UPDATE action_version
        SET status = 'published', is_active = 1, published_at = :ts
        WHERE action_version_id = :id"""),
        {"id": action_version_id, "ts": timestamp})

    # Update parent definition timestamp
    db.execute(text("""
        UPDATE action_definition SET updated_at = :ts
        WHERE action_definition_id = :ad_id"""),
        {"ad_id": ad_id, "ts": timestamp})

    return {
        "action_version_id": action_version_id,
        "version": row["version"],
        "status": "published",
        "published_at": timestamp,
    }


# =========================================================================
# Create Draft from Published
# =========================================================================
def create_draft_from_published(db: Session, from_version_id: str, user_id: str) -> dict:
    """Clone a published version into a new draft with a bumped minor version."""
    row = db.execute(text("""
        SELECT * FROM action_version
        WHERE action_version_id = :id"""),
        {"id": from_version_id}).mappings().first()
    if not row:
        action_version_not_found()

    source = dict(row)
    # Bump minor version: 0.1.0 -> 0.2.0
    parts = source["version"].split(".")
    parts[1] = str(int(parts[1]) + 1)
    new_version = ".".join(parts)

    new_id = generate_unique_id("av_")
    timestamp = generate_utc_timestamp()

    db.execute(text("""
        INSERT INTO action_version
        (action_version_id, action_definition_id, version, status, is_active,
         inputs_schema_json, execution_json, outputs_schema_json,
         configurations_json, ui_form_json, policy_json,
         created_by, created_at)
        VALUES (:id, :ad_id, :version, 'draft', 0,
                :inputs, :execution, :outputs, :configurations, :ui_form, :policy,
                :user, :ts)"""),
        {"id": new_id, "ad_id": source["action_definition_id"], "version": new_version,
         "inputs": source.get("inputs_schema_json"),
         "execution": source.get("execution_json"),
         "outputs": source.get("outputs_schema_json"),
         "configurations": source.get("configurations_json"),
         "ui_form": source.get("ui_form_json"),
         "policy": source.get("policy_json"),
         "user": user_id, "ts": timestamp})

    return {
        "action_version_id": new_id,
        "from_version_id": from_version_id,
        "version": new_version,
        "status": "draft",
    }
