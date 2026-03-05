"""
Skill service — business logic for the Skills Library (list page).
"""
from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.common.errors import skill_name_exists, skill_key_exists
from app.common.utils import generate_unique_id
from app.skill import repository as skill_repository
from app.skill_graph.repository import clone_graph, create_blank_graph
from app.logger.logging import logger


def list_all_skills(
    db: Session,
    client_id: Optional[str] = None,
    status: Optional[str] = None,
    search_query: Optional[str] = None,
) -> Dict:
    items = skill_repository.fetch_all_skills(db, client_id=client_id, status=status, search_query=search_query)
    return {"items": items, "total": len(items)}


def create_skill(db: Session, request, user_id: str) -> Dict:
    """Create a new Skill with an initial draft version and starter graph.
    Returns only skill_id and skill_version_id."""
    if skill_repository.does_skill_name_exist(db, request.client_id, request.payer_id, request.name):
        skill_name_exists()

    skill_key = request.skill_key or skill_repository.suggest_skill_key(db, request.client_id, request.name)
    if skill_repository.does_skill_key_exist(db, request.client_id, skill_key):
        skill_key_exists()

    skill_id = generate_unique_id("skill_")
    skill_version_id = generate_unique_id("sv_")

    skill_repository.insert_skill(
        db, skill_id=skill_id, client_id=request.client_id, payer_id=request.payer_id,
        name=request.name, skill_key=skill_key, description=request.description,
        category=request.category, owner_user_id=request.owner_user_id,
        owner_team_id=request.owner_team_id, created_by=user_id,
    )
    skill_repository.insert_skill_version(
        db, skill_version_id=skill_version_id, skill_id=skill_id,
        environment=request.environment, created_by=user_id,
    )

    if request.start_from.mode == "blank":
        create_blank_graph(db, skill_version_id)
    elif request.start_from.mode == "clone" and request.start_from.clone:
        clone_graph(db, new_skill_version_id=skill_version_id,
                    source_skill_version_id=request.start_from.clone.source_skill_version_id)

    if request.tags:
        tag_ids = skill_repository.upsert_tags(db, request.tags)
        skill_repository.attach_tags_to_skill(db, skill_id, tag_ids)

    logger.info(f"Created skill '{request.name}' (key={skill_key}, id={skill_id})")

    return {
        "skill_id": skill_id,
        "skill_version_id": skill_version_id,
    }
