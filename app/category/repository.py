from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.common.utils import generate_unique_id
from app.category.models import CategoryResponse

def list_categories(db: Session) -> List[CategoryResponse]:
    rows = db.execute(text("SELECT category_id, name, description FROM category ORDER BY name ASC")).mappings().all()
    return [CategoryResponse(**dict(row)) for row in rows]

def get_category(db: Session, category_id: int) -> CategoryResponse | None:
    row = db.execute(
        text("SELECT category_id, name, description FROM category WHERE category_id = :id"),
        {"id": category_id}
    ).mappings().first()
    return CategoryResponse(**dict(row)) if row else None

def create_category(db: Session, name: str, description: str | None) -> CategoryResponse | None:
    res = db.execute(
        text("INSERT INTO category (name, description) VALUES (:name, :desc)"),
        {"name": name, "desc": description}
    )
    db.commit()
    # In SQLite with SQLAlchemy, lastrowid is available on the Result object
    return get_category(db, res.lastrowid)

def update_category(db: Session, category_id: int, name: str | None, description: str | None) -> CategoryResponse | None:
    current = get_category(db, category_id)
    if not current:
        return None
    new_name = name if name is not None else current.name
    new_desc = description if description is not None else current.description
    db.execute(
        text("UPDATE category SET name = :name, description = :desc WHERE category_id = :id"),
        {"id": category_id, "name": new_name, "desc": new_desc}
    )
    db.commit()
    return get_category(db, category_id)

def can_delete_category(db: Session, category_id: int) -> bool:
    action_ref = db.execute(
        text("SELECT 1 FROM action_definition WHERE category_id = :id LIMIT 1"),
        {"id": category_id}
    ).mappings().first()
    if action_ref:
        return False

    skill_ref = db.execute(
        text("SELECT 1 FROM skill WHERE category_id = :id LIMIT 1"),
        {"id": category_id}
    ).mappings().first()
    if skill_ref:
        return False
        
    return True

def delete_category(db: Session, category_id: int) -> bool:
    res = db.execute(text("DELETE FROM category WHERE category_id = :id"), {"id": category_id})
    db.commit()
    return res.rowcount > 0
