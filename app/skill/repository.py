"""
Skill repository — database queries for skill metadata, tags, and listing.
"""
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.common.utils import generate_unique_id, generate_utc_timestamp, serialise_json


def suggest_skill_key(db: Session, client_id: str, skill_name: str) -> str:
    """Auto-generate a unique skill key like D01, D02, etc."""
    first_letter = (skill_name.strip()[:1] or "S").upper()
    existing_rows = db.execute(
        text("SELECT skill_key FROM skill WHERE client_id = :client_id AND skill_key LIKE :pattern"),
        {"client_id": client_id, "pattern": f"{first_letter}%"},
    ).mappings().all()
    existing_keys = {row["skill_key"] for row in existing_rows}

    for sequence_number in range(1, 1000):
        candidate_key = f"{first_letter}{sequence_number:02d}"
        if candidate_key not in existing_keys:
            return candidate_key
    return f"{first_letter}{uuid.uuid4().hex[:6].upper()}"


def does_skill_name_exist(db: Session, client_id: str, payer_id: Optional[str], name: str) -> bool:
    row = db.execute(
        text("SELECT 1 FROM skill WHERE client_id=:client_id AND COALESCE(payer_id,'')=COALESCE(:payer_id,'') AND name=:name LIMIT 1"),
        {"client_id": client_id, "payer_id": payer_id, "name": name},
    ).mappings().first()
    return row is not None


def does_skill_key_exist(db: Session, client_id: str, skill_key: str) -> bool:
    row = db.execute(
        text("SELECT 1 FROM skill WHERE client_id=:client_id AND skill_key=:skill_key LIMIT 1"),
        {"client_id": client_id, "skill_key": skill_key},
    ).mappings().first()
    return row is not None


def upsert_tags(db: Session, tag_names: List[str]) -> List[str]:
    """Insert tags if they do not exist. Returns a list of tag IDs."""
    tag_ids = []
    for tag_name in tag_names:
        existing_row = db.execute(
            text("SELECT tag_id FROM tag WHERE name=:name"), {"name": tag_name}
        ).mappings().first()
        if existing_row:
            tag_ids.append(existing_row["tag_id"])
        else:
            new_tag_id = generate_unique_id("tag_")
            db.execute(
                text("INSERT INTO tag (tag_id, name) VALUES (:tag_id, :name)"),
                {"tag_id": new_tag_id, "name": tag_name},
            )
            tag_ids.append(new_tag_id)
    return tag_ids


def attach_tags_to_skill(db: Session, skill_id: str, tag_ids: List[str]) -> None:
    for tag_id in tag_ids:
        db.execute(
            text("INSERT OR IGNORE INTO skill_tag (skill_id, tag_id) VALUES (:skill_id, :tag_id)"),
            {"skill_id": skill_id, "tag_id": tag_id},
        )


def insert_skill(
    db: Session,
    skill_id: str, client_id: str, payer_id: Optional[str],
    name: str, skill_key: str, description: Optional[str],
    category: Optional[str], owner_user_id: Optional[str],
    owner_team_id: Optional[str], created_by: str,
) -> None:
    timestamp = generate_utc_timestamp()
    db.execute(
        text("""INSERT INTO skill
           (skill_id, client_id, payer_id, name, skill_key, description,
            category, owner_user_id, owner_team_id, metadata_json,
            created_by, created_at, updated_at)
           VALUES (:skill_id, :client_id, :payer_id, :name, :skill_key, :description,
                   :category, :owner_user_id, :owner_team_id, :metadata_json,
                   :created_by, :created_at, :updated_at)"""),
        {
            "skill_id": skill_id, "client_id": client_id, "payer_id": payer_id,
            "name": name, "skill_key": skill_key, "description": description,
            "category": category, "owner_user_id": owner_user_id,
            "owner_team_id": owner_team_id, "metadata_json": serialise_json({}),
            "created_by": created_by, "created_at": timestamp, "updated_at": timestamp,
        },
    )


def insert_skill_version(
    db: Session,
    skill_version_id: str, skill_id: str,
    environment: str, created_by: str, version: str = "0.1.0",
) -> None:
    db.execute(
        text("""INSERT INTO skill_version
           (skill_version_id, skill_id, environment, version, status, is_active, created_by, created_at)
           VALUES (:skill_version_id, :skill_id, :environment, :version, 'draft', 1, :created_by, :created_at)"""),
        {
            "skill_version_id": skill_version_id, "skill_id": skill_id,
            "environment": environment, "version": version,
            "created_by": created_by, "created_at": generate_utc_timestamp(),
        },
    )


def fetch_all_skills(
    db: Session,
    client_id: Optional[str] = None,
    status: Optional[str] = None,
    search_query: Optional[str] = None,
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
            "category": skill_row["category"],
            "tags": associated_tags,
            "latest_version_id": skill_row["latest_version_id"],
            "version": skill_row["version"],
            "status": skill_row["version_status"],
            "environment": skill_row["environment"],
            "updated_at": skill_row["updated_at"],
        })
    return result_items
