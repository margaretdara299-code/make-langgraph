"""
Skill service — business logic for the Skills Library (list page).
"""
from typing import Dict
from sqlalchemy.orm import Session
from app.common.errors import skill_name_exists, skill_key_exists
from app.common.utils import generate_unique_id
from app.skill import repository as skill_repository
from app.skill_graph.repository import clone_graph, create_blank_graph
from app.logger.logging import logger


def list_all_skills(
    db: Session,
    client_id: str | None = None,
    status: str | None = None,
    search_query: str | None = None,
) -> Dict:
    items = skill_repository.fetch_all_skills(db, client_id=client_id, status=status, search_query=search_query)
    return {"items": items, "total": len(items)}


def create_skill(db: Session, request, user_id: str = "1") -> Dict:
    """Create a new Skill with an initial draft version and starter graph.
    Returns only skill_id and skill_version_id."""
    if skill_repository.does_skill_name_exist(db, request.client_id, request.name):
        skill_name_exists()

    skill_key = request.skill_key or skill_repository.suggest_skill_key(db, request.client_id, request.name)
    if skill_repository.does_skill_key_exist(db, request.client_id, skill_key):
        skill_key_exists()

    skill_id = generate_unique_id("skill_")
    skill_version_id = generate_unique_id("sv_")

    skill_repository.insert_skill(
        db, skill_id=skill_id, client_id=request.client_id,
        name=request.name, skill_key=skill_key, description=request.description,
        category=request.category, created_by=user_id,
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


def get_skill_graph(db: Session, skill_version_id: str) -> dict | None:
    """Load the graph (nodes + connections) for a skill version."""
    return skill_repository.fetch_skill_graph(db, skill_version_id)


def save_graph(db: Session, skill_version_id: str, nodes: list, connections: dict) -> dict:
    """Bulk-save the entire graph for a skill version."""
    result = skill_repository.save_skill_graph(db, skill_version_id, nodes, connections)
    logger.info(f"Saved graph for skill version '{skill_version_id}': {result['node_count']} nodes, {result['connection_count']} connections")
    return result


def update_node(db: Session, skill_version_id: str, node_id: str, data: dict) -> dict | None:
    """Update a single node's configuration data."""
    result = skill_repository.update_single_node(db, skill_version_id, node_id, data)
    if result:
        logger.info(f"Updated node '{node_id}' in skill version '{skill_version_id}'")
    return result
