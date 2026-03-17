"""
Action repository — simplified, no versioning.
One action_definition + one action_version (JSON blobs only) per action.
"""
import json
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.common.errors import action_not_found, action_key_exists, action_name_exists
from app.common.utils import generate_unique_id, generate_utc_timestamp


def serialize_to_json(value) -> str:
    """Serialize a value to a compact JSON string. Returns '{}' for falsy values."""
    if not value and value != 0 and value is not False:
        return '{}'
    return json.dumps(value, separators=(',', ':'))


def deserialize_json(value, default=None):
    """Deserialize a JSON string. Returns default on failure."""
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


# =========================================================================
# CREATE
# =========================================================================
def insert_action(db: Session, request, user_id: str) -> dict:
    """Create a new action_definition + one action_version (JSON blobs)."""
    timestamp = generate_utc_timestamp()
    action_definition_id = generate_unique_id("ad_")
    action_version_id = generate_unique_id("av_")

    # Duplicate name check
    existing_name = db.execute(
        text("SELECT 1 FROM action_definition WHERE name = :name"),
        {"name": request.name}
    ).first()
    if existing_name:
        action_name_exists()

    # Insert action_definition
    try:
        db.execute(text("""
            INSERT INTO action_definition
              (action_definition_id, action_key, name, description, category,
               capability, icon, default_node_title, scope, client_id,
               status, is_active, created_by, created_at, updated_at)
            VALUES
              (:id, :key, :name, :desc, :cat,
               :cap, :icon, :title, :scope, :client,
               :status, :is_active, :user, :ts, :ts)
        """), {
            "id": action_definition_id,
            "key": request.action_key,
            "name": request.name,
            "desc": request.description,
            "cat": request.category,
            "cap": request.capability,
            "icon": request.icon,
            "title": request.default_node_title,
            "scope": request.scope or "global",
            "client": request.client_id or "1",
            "status": request.status or "published",
            "is_active": 1 if request.is_active else 0,
            "user": user_id,
            "ts": timestamp,
        })
    except IntegrityError:
        action_key_exists()

    # Insert action_version — only JSON blobs used, no versioning columns
    db.execute(text("""
        INSERT INTO action_version
          (action_version_id, action_definition_id,
           inputs_schema_json, execution_json, outputs_schema_json,
           configurations_json, ui_form_json, policy_json)
        VALUES
          (:av_id, :ad_id,
           :inputs, :execution, :outputs,
           :configurations, :ui_form, :policy)
    """), {
        "av_id": action_version_id,
        "ad_id": action_definition_id,
        "inputs": serialize_to_json(request.inputs_schema_json),
        "execution": serialize_to_json(request.execution_json),
        "outputs": serialize_to_json(request.outputs_schema_json),
        "configurations": serialize_to_json(request.configurations_json),
        "ui_form": serialize_to_json(request.ui_form_json),
        "policy": serialize_to_json(request.policy_json),
    })

    return {
        "action_definition_id": action_definition_id,
        "name": request.name,
        "action_key": request.action_key,
        "status": request.status or "published",
        "is_active": request.is_active,
    }


# =========================================================================
# GET ALL
# =========================================================================
def fetch_all_actions(db: Session,
                      status: str | None = None,
                      capability: str | None = None,
                      category: str | None = None,
                      search_query: str | None = None) -> list:
    """List all actions with their JSON blobs joined from action_version."""
    where = ["1=1"]
    params = {}
    if status:
        where.append("ad.status = :status")
        params["status"] = status
    if capability:
        where.append("ad.capability = :capability")
        params["capability"] = capability
    if category:
        if category.lower() == "uncategorized":
            where.append("(ad.category IS NULL OR ad.category = '')")
        else:
            where.append("ad.category = :category")
            params["category"] = category
    if search_query:
        where.append("(ad.name LIKE :q OR ad.action_key LIKE :q)")
        params["q"] = f"%{search_query}%"

    rows = db.execute(text(f"""
        SELECT
            ad.action_definition_id, ad.action_key, ad.name, ad.description,
            ad.category, ad.capability, ad.icon, ad.default_node_title,
            ad.scope, ad.status, ad.is_active, ad.updated_at
        FROM action_definition ad
        WHERE {" AND ".join(where)}
        ORDER BY ad.updated_at DESC
    """), params).mappings().all()

    return [dict(r) for r in rows]


# =========================================================================
# GET BY ID
# =========================================================================
def fetch_action_by_id(db: Session, action_definition_id: str) -> dict | None:
    """Get a single action with its JSON blobs."""
    row = db.execute(text("""
        SELECT
            ad.action_definition_id, ad.action_key, ad.name, ad.description,
            ad.category, ad.capability, ad.icon, ad.default_node_title,
            ad.scope, ad.client_id,
            ad.status      AS status,
            ad.is_active   AS is_active,
            ad.created_at, ad.updated_at,
            av.action_version_id,
            av.inputs_schema_json, av.execution_json, av.outputs_schema_json,
            av.configurations_json, av.ui_form_json, av.policy_json
        FROM action_definition ad
        LEFT JOIN action_version av
            ON av.action_definition_id = ad.action_definition_id
        WHERE ad.action_definition_id = :id
        LIMIT 1
    """), {"id": action_definition_id}).fetchone()

    if not row:
        return None

    keys = ["action_definition_id", "action_key", "name", "description",
            "category", "capability", "icon", "default_node_title",
            "scope", "client_id", "status", "is_active",
            "created_at", "updated_at", "action_version_id",
            "inputs_schema_json", "execution_json", "outputs_schema_json",
            "configurations_json", "ui_form_json", "policy_json"]
    action_dict = dict(zip(keys, row))
    action_dict["inputs_schema_json"] = deserialize_json(action_dict.get("inputs_schema_json"), {})
    action_dict["execution_json"] = deserialize_json(action_dict.get("execution_json"), {})
    action_dict["outputs_schema_json"] = deserialize_json(action_dict.get("outputs_schema_json"), {})
    action_dict["configurations_json"] = deserialize_json(action_dict.get("configurations_json"), {})
    action_dict["ui_form_json"] = deserialize_json(action_dict.get("ui_form_json"), {})
    action_dict["policy_json"] = deserialize_json(action_dict.get("policy_json"), {})
    return action_dict


# =========================================================================
# UPDATE
# =========================================================================
def update_action(db: Session, action_definition_id: str, request) -> dict:
    """Update action_definition metadata + JSON blobs in action_version."""
    row = db.execute(
        text("SELECT action_definition_id, name FROM action_definition WHERE action_definition_id = :id"),
        {"id": action_definition_id}
    ).first()
    if not row:
        action_not_found()

    # Duplicate name check (exclude self)
    if request.name is not None:
        existing = db.execute(
            text("SELECT 1 FROM action_definition WHERE name = :name AND action_definition_id != :id"),
            {"name": request.name, "id": action_definition_id}
        ).first()
        if existing:
            action_name_exists()

    timestamp = generate_utc_timestamp()

    # Update action_definition fields
    update_data = request.model_dump(exclude_unset=True)
    
    action_def_fields = {}
    for field_name in ["name", "action_key", "description", "category", "capability", "icon", "default_node_title", "scope", "status"]:
        if field_name in update_data:
            action_def_fields[field_name] = update_data[field_name]
            
    if "is_active" in update_data:
        action_def_fields["is_active"] = 1 if update_data["is_active"] else 0

    if action_def_fields:
        set_clauses = [f"{field_name} = :{field_name}" for field_name in action_def_fields.keys()]
        set_clauses.append("updated_at = :ts")
        params = dict(action_def_fields)
        params.update({"id": action_definition_id, "ts": timestamp})
        
        try:
            db.execute(text(f"""
                UPDATE action_definition SET {', '.join(set_clauses)}
                WHERE action_definition_id = :id
            """), params)
        except IntegrityError:
            action_key_exists()

    # Update action_version JSON blobs
    action_ver_fields = {}
    json_keys = ["inputs_schema_json", "execution_json", "outputs_schema_json", "configurations_json", "ui_form_json", "policy_json"]
    for field_name in json_keys:
        if field_name in update_data:
            action_ver_fields[field_name] = serialize_to_json(update_data[field_name])
            
    if action_ver_fields:
        action_ver_set_clauses = [f"{field_name} = :{field_name}" for field_name in action_ver_fields.keys()]
        action_ver_params = dict(action_ver_fields)
        action_ver_params["id"] = action_definition_id
        db.execute(text(f"""
            UPDATE action_version SET {', '.join(action_ver_set_clauses)}
            WHERE action_definition_id = :id
        """), action_ver_params)

    return {"action_definition_id": action_definition_id, "updated_at": timestamp}


# =========================================================================
# UPDATE STATUS ONLY
# =========================================================================
def update_action_status(db: Session, action_definition_id: str, request) -> dict:
    """Update only the status and is_active fields of an action."""
    row = db.execute(
        text("SELECT action_definition_id FROM action_definition WHERE action_definition_id = :id"),
        {"id": action_definition_id}
    ).first()
    if not row:
        action_not_found()

    timestamp = generate_utc_timestamp()
    action_def_fields = {}
    
    if request.status is not None:
        action_def_fields["status"] = request.status
    if request.is_active is not None:
        action_def_fields["is_active"] = 1 if request.is_active else 0

    if not action_def_fields:
        return {"action_definition_id": action_definition_id, "message": "No changes requested"}

    set_clauses = [f"{field_name} = :{field_name}" for field_name in action_def_fields.keys()]
    set_clauses.append("updated_at = :ts")
    
    params = dict(action_def_fields)
    params.update({"id": action_definition_id, "ts": timestamp})

    db.execute(text(f"""
        UPDATE action_definition SET {', '.join(set_clauses)}
        WHERE action_definition_id = :id
    """), params)

    return {"action_definition_id": action_definition_id, "updated_at": timestamp}
