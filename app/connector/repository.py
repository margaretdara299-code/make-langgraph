"""
Connector Repository — raw SQL / SQLAlchemy operations for the connector table.
"""
import json
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from app.logger.logging import logger


def fetch_all_connectors(db: Session, is_active: bool | None = None) -> list:
    """Fetch all connectors from the database."""
    where = []
    params = {}
    if is_active is not None:
        where.append("is_active = :is_active")
        params["is_active"] = 1 if is_active else 0

    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    query = f"SELECT * FROM connector {where_clause} ORDER BY created_at DESC"
    
    rows = db.execute(text(query), params).mappings().all()
    result = []
    for r in rows:
        d = dict(r)
        d["config_json"] = json.loads(d["config_json"])
        result.append(d)
    return result


def fetch_connectors_grouped(db: Session) -> dict[str, list[dict]]:
    """Fetch all connectors and group them by their connector_type."""
    query = "SELECT * FROM connector ORDER BY connector_type ASC, name ASC"
    rows = db.execute(text(query)).mappings().all()
    
    grouped_connectors: dict[str, list[dict]] = {}
    
    for r in rows:
        connector_data = dict(r)
        connector_data["config_json"] = json.loads(connector_data["config_json"])
        
        c_type = connector_data.get("connector_type") or "Unknown"
        # Standardize typing for the key (e.g., uppercase)
        group_key = c_type.upper()
        
        if group_key not in grouped_connectors:
            grouped_connectors[group_key] = []
        
        grouped_connectors[group_key].append(connector_data)
        
    return grouped_connectors


def fetch_connector_by_id(db: Session, connector_id: int) -> dict | None:
    """Fetch a single connector by its integer ID."""
    row = db.execute(
        text("SELECT * FROM connector WHERE connector_id = :id"),
        {"id": connector_id}
    ).mappings().first()
    
    if not row:
        return None
    
    d = dict(row)
    d["config_json"] = json.loads(d["config_json"])
    return d


def create_connector(db: Session, request) -> dict:
    """Insert a new connector into the database."""
    now = datetime.now().isoformat()
    config_str = json.dumps(request.config_json)
    
    res = db.execute(
        text("""
            INSERT INTO connector (name, connector_type, description, config_json, is_active, created_at, updated_at)
            VALUES (:name, :type, :desc, :config, :active, :now, :now)
        """),
        {
            "name": request.name,
            "type": request.connector_type,
            "desc": request.description,
            "config": config_str,
            "active": 1 if request.is_active else 0,
            "now": now
        }
    )
    db.commit()
    new_id = res.lastrowid
    return fetch_connector_by_id(db, new_id)


def update_connector(db: Session, connector_id: int, request) -> dict:
    """Update an existing connector's metadata."""
    updates = []
    params = {"id": connector_id, "now": datetime.now().isoformat()}
    
    if request.name is not None:
        updates.append("name = :name")
        params["name"] = request.name
    if request.connector_type is not None:
        updates.append("connector_type = :type")
        params["type"] = request.connector_type
    if request.description is not None:
        updates.append("description = :desc")
        params["desc"] = request.description
    if request.config_json is not None:
        updates.append("config_json = :config")
        params["config"] = json.dumps(request.config_json)
    if request.status is not None:
        updates.append("status = :status")
        params["status"] = request.status
    if request.is_active is not None:
        updates.append("is_active = :active")
        params["active"] = 1 if request.is_active else 0

    if not updates:
        return fetch_connector_by_id(db, connector_id)

    updates.append("updated_at = :now")
    query = f"UPDATE connector SET {', '.join(updates)} WHERE connector_id = :id"
    db.execute(text(query), params)
    db.commit()
    
    return fetch_connector_by_id(db, connector_id)


def delete_connector(db: Session, connector_id: int) -> bool:
    """Delete a connector."""

    db.execute(
        text("DELETE FROM connector WHERE connector_id = :id"),
        {"id": connector_id}
    )
    db.commit()
    return True
