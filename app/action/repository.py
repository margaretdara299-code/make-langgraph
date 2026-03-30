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
    """Serialize a value to a compact JSON string. Handles list/dict/None correctly."""
    if value is None:
        return '{}'
    if isinstance(value, list) and not value:
        return '[]'
    if isinstance(value, dict) and not value:
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
def insert_action(db: Session, request, user_id: int) -> dict:
    """Create a new action_definition + one action_version (JSON blobs)."""
    timestamp = generate_utc_timestamp()

    # Duplicate name or key check
    existing = db.execute(
        text("SELECT name, action_key FROM action_definition WHERE name = :name OR action_key = :key"),
        {"name": request.name, "key": request.action_key}
    ).first()
    if existing:
        if existing[0] == request.name:
            action_name_exists()
        else:
            action_key_exists()

    # Insert action_definition
    try:
        res_def = db.execute(text("""
            INSERT INTO action_definition
              (action_key, name, description, category_id,
               capability_id, icon, default_node_title, scope, client_id,
               status, is_active, created_by, created_at, updated_at)
            VALUES
              (:key, :name, :desc, :cat,
               :cap, :icon, :title, :scope, :client,
               :status, :is_active, :user, :ts, :ts)
        """), {
            "key": request.action_key,
            "name": request.name,
            "desc": request.description,
            "cat": request.category_id,
            "cap": request.capability_id,
            "icon": request.icon,
            "title": request.default_node_title,
            "scope": request.scope or "global",
            "client": request.client_id or 1,
            "status": request.status or "published",
            "is_active": 1 if request.is_active else 0,
            "user": user_id,
            "ts": timestamp,
        })
        action_definition_id = res_def.lastrowid
    except IntegrityError as e:
        error_msg = str(e).lower()
        print(f"DEBUG: IntegrityError when inserting action: {e}")
        if "foreign key" in error_msg:
            # Determine if it was category or capability
            if "category_id" in error_msg:
                from app.common.response import raise_bad_request
                raise_bad_request(f"Invalid category_id: {request.category_id}")
            elif "capability_id" in error_msg:
                from app.common.response import raise_bad_request
                raise_bad_request(f"Invalid capability_id: {request.capability_id}")
            else:
                from app.common.response import raise_bad_request
                raise_bad_request("One or more referenced IDs (category/capability) are invalid.")
        else:
            action_key_exists()

    # Insert action_version — only JSON blobs used, no versioning columns
    res_ver = db.execute(text("""
        INSERT INTO action_version
          (action_definition_id,
           inputs_schema_json, execution_json, outputs_schema_json,
           configurations_json, ui_form_json, policy_json)
        VALUES
          (:ad_id,
           :inputs, :execution, :outputs,
           :configurations, :ui_form, :policy)
    """), {
        "ad_id": action_definition_id,
        "inputs": serialize_to_json(None),
        "execution": serialize_to_json(None),
        "outputs": serialize_to_json(None),
        "configurations": serialize_to_json(request.configurations_json),
        "ui_form": serialize_to_json(None),
        "policy": serialize_to_json(None),
    })
    action_version_id = res_ver.lastrowid

    db.commit()

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
                      capability_id: int | None = None,
                      category_id: int | None = None,
                      search_query: str | None = None) -> list:
    """List all actions with their JSON blobs joined from action_version."""
    where = ["1=1"]
    params = {}
    if status:
        where.append("ad.status = :status")
        params["status"] = status
    if capability_id:
        where.append("ad.capability_id = :capability_id")
        params["capability_id"] = capability_id
    if category_id:
        where.append("ad.category_id = :category_id")
        params["category_id"] = category_id
    if search_query:
        where.append("(ad.name LIKE :q OR ad.action_key LIKE :q)")
        params["q"] = f"%{search_query}%"

    rows = db.execute(text(f"""
        SELECT
            ad.action_definition_id, ad.action_key, ad.name, ad.description,
            ad.category_id, ad.capability_id, ad.icon, ad.default_node_title,
            ad.scope, ad.status, ad.is_active, ad.updated_at
        FROM action_definition ad
        WHERE {" AND ".join(where)}
        ORDER BY ad.updated_at DESC
    """), params).mappings().all()

    return [dict(r) for r in rows]


def fetch_actions_grouped_by_category(db: Session) -> dict:
    """Retrieve all actions joined with categories and group them by category name."""
    rows = db.execute(text("""
        SELECT 
            c.name as category_name,
            ad.action_definition_id, ad.action_key, ad.name, ad.description, ad.icon
        FROM action_definition ad
        LEFT JOIN category c ON ad.category_id = c.category_id
        ORDER BY c.name, ad.name
    """)).mappings().all()
    
    grouped = {}
    for row in rows:
        cat_name = row["category_name"] or "Uncategorized"
        if cat_name not in grouped:
            grouped[cat_name] = []
        
        grouped[cat_name].append({
            "action_definition_id": row["action_definition_id"],
            "action_key": row["action_key"],
            "name": row["name"],
            "description": row["description"],
            "icon": row["icon"]
        })
    return grouped


# =========================================================================
# GET BY ID
# =========================================================================
def fetch_action_by_id(db: Session, action_definition_id: int) -> dict | None:
    """Get a single action with its JSON blobs."""
    row = db.execute(text("""
        SELECT
            ad.action_definition_id, ad.action_key, ad.name, ad.description,
            ad.category_id, ad.capability_id, ad.icon, ad.default_node_title,
            ad.scope, ad.client_id,
            ad.status      AS status,
            ad.is_active   AS is_active,
            ad.created_at, ad.updated_at,
            av.action_version_id,            
            av.configurations_json
        FROM action_definition ad
        LEFT JOIN action_version av
            ON av.action_definition_id = ad.action_definition_id
        WHERE ad.action_definition_id = :id
        LIMIT 1
    """), {"id": action_definition_id}).fetchone()

    if not row:
        return None

    keys = ["action_definition_id", "action_key", "name", "description",
            "category_id", "capability_id", "icon", "default_node_title",
            "scope", "client_id", "status", "is_active",
            "created_at", "updated_at", "action_version_id",             
            "configurations_json"]
    action_dict = dict(zip(keys, row))
    action_dict["configurations_json"] = deserialize_json(action_dict.get("configurations_json"), {})
    return action_dict

# =========================================================================
# UPDATE
# =========================================================================
def update_action(db: Session, action_definition_id: int, request) -> dict:
    """Update action_definition metadata + JSON blobs in action_version."""
    row = db.execute(
        text("SELECT action_definition_id, name FROM action_definition WHERE action_definition_id = :id"),
        {"id": action_definition_id}
    ).first()
    if not row:
        action_not_found()

    # Duplicate name or key check (exclude self)
    if request.name is not None or request.action_key is not None:
        name_val = request.name or row[1]
        # Query for both name and key, excluding current ID
        # If action_key is missing in request, we check against current value if name is provided
        # or we just check the provided key.
        # However, it's safer to always check the new key if it exists.
        
        # Determine values to check
        check_name = request.name or ""
        check_key = request.action_key or ""
        
        where_clauses = ["action_definition_id != :id"]
        params = {"id": action_definition_id}
        
        if request.name and request.action_key:
            where_clauses.append("(name = :name OR action_key = :key)")
            params["name"] = request.name
            params["key"] = request.action_key
        elif request.name:
            where_clauses.append("name = :name")
            params["name"] = request.name
        else: # only request.action_key
            where_clauses.append("action_key = :key")
            params["key"] = request.action_key
            
        existing = db.execute(
            text(f"SELECT name, action_key FROM action_definition WHERE {' AND '.join(where_clauses)}"),
            params
        ).first()
        
        if existing:
            if request.name and existing[0] == request.name:
                action_name_exists()
            if request.action_key and existing[1] == request.action_key:
                action_key_exists()

    timestamp = generate_utc_timestamp()

    # Update action_definition fields
    update_data = request.model_dump(exclude_unset=True)
    
    action_def_fields = {}
    for field_name in ["name", "action_key", "description", "category_id", "capability_id", "icon", "default_node_title", "scope", "status"]:
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
        except IntegrityError as e:
            error_msg = str(e).lower()
            if "foreign key" in error_msg:
                from app.common.response import raise_bad_request
                raise_bad_request("Invalid category_id or capability_id")
            action_key_exists()

    # Update action_version JSON blobs
    action_ver_fields = {}
    json_keys = ["configurations_json"]
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

    db.commit()

    return {"action_definition_id": action_definition_id, "updated_at": timestamp}


# =========================================================================
# UPDATE STATUS ONLY
# =========================================================================
def update_action_status(db: Session, action_definition_id: int, request) -> dict:
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

    db.commit()

    return {"action_definition_id": action_definition_id, "updated_at": timestamp}


# =========================================================================
# DELETE
# =========================================================================
def is_action_in_use(db: Session, action_key: str) -> bool:
    """Check if the action_key is referenced in any skill_version.nodes JSON."""
    # Search for the action_key inside the nodes JSON blob
    # Designer uses node type for action nodes (e.g. "action.my_action_key")
    # or sometimes stores it in data.action_key.
    query = text("""
        SELECT 1 FROM skill_version 
        WHERE nodes LIKE :p1 
           OR nodes LIKE :p2
        LIMIT 1
    """)
    # Broad patterns to catch both "type" and "action_key" references
    p1 = f'%"type":"action.{action_key}"%'
    p2 = f'%"action_key":"{action_key}"%'
    
    result = db.execute(query, {"p1": p1, "p2": p2}).first()
    return result is not None


def delete_action(db: Session, action_definition_id: int) -> bool:
    """Delete an action definition if it's not in use."""
    row = db.execute(
        text("SELECT action_key FROM action_definition WHERE action_definition_id = :id"),
        {"id": action_definition_id}
    ).first()
    
    if not row:
        action_not_found()

    action_key = row[0]
    
    if is_action_in_use(db, action_key):
        return False # Indicates "In Use"

    # Explicitly delete versions first for extra safety
    db.execute(
        text("DELETE FROM action_version WHERE action_definition_id = :id"),
        {"id": action_definition_id}
    )

    # Then delete the definition
    db.execute(
        text("DELETE FROM action_definition WHERE action_definition_id = :id"),
        {"id": action_definition_id}
    )
    db.commit()
    return True

