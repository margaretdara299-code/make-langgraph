from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.common.utils import generate_unique_id
from app.capability.models import CapabilityResponse

def list_capabilities(db: Session) -> List[CapabilityResponse]:
    rows = db.execute(text("SELECT capability_id, name, description FROM capability ORDER BY name ASC")).mappings().all()
    return [CapabilityResponse(**dict(row)) for row in rows]

def get_capability(db: Session, capability_id: int) -> CapabilityResponse | None:
    row = db.execute(
        text("SELECT capability_id, name, description FROM capability WHERE capability_id = :id"),
        {"id": capability_id}
    ).mappings().first()
    return CapabilityResponse(**dict(row)) if row else None

def create_capability(db: Session, name: str, description: str | None) -> CapabilityResponse | None:
    res = db.execute(
        text("INSERT INTO capability (name, description) VALUES (:name, :desc)"),
        {"name": name, "desc": description}
    )
    db.commit()
    return get_capability(db, res.lastrowid)

def update_capability(db: Session, capability_id: int, name: str | None, description: str | None) -> CapabilityResponse | None:
    current = get_capability(db, capability_id)
    if not current:
        return None
    new_name = name if name is not None else current.name
    new_desc = description if description is not None else current.description
    db.execute(
        text("UPDATE capability SET name = :name, description = :desc WHERE capability_id = :id"),
        {"id": capability_id, "name": new_name, "desc": new_desc}
    )
    db.commit()
    return get_capability(db, capability_id)

def can_delete_capability(db: Session, capability_id: int) -> bool:
    action_ref = db.execute(
        text("SELECT 1 FROM action_definition WHERE capability_id = :id LIMIT 1"),
        {"id": capability_id}
    ).mappings().first()
    if action_ref:
        return False
        
    return True

def delete_capability(db: Session, capability_id: int) -> bool:
    res = db.execute(text("DELETE FROM capability WHERE capability_id = :id"), {"id": capability_id})
    db.commit()
    return res.rowcount > 0
