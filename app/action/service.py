"""
Action service — business logic for the Action Catalog.
"""
from sqlalchemy.orm import Session
from app.action import repository as action_repository
from app.logger.logging import logger


def list_all_actions(db: Session, status: str | None = None, capability: str | None = None,
                     category: str | None = None, search_query: str | None = None) -> dict:
    items = action_repository.fetch_all_actions(db, status=status, capability=capability,
                                                 category=category, search_query=search_query)
    return {"items": items, "total": len(items)}


def create_action_definition(db: Session, request, user_id: str) -> dict:
    result = action_repository.insert_action_definition(db, request, user_id)
    logger.info(f"Created action '{request.name}' (key={request.action_key})")
    return result


def get_designer_actions(db: Session, client_id: str, environment: str = "dev",
                         capability: str | None = None, category: str | None = None,
                         search_query: str | None = None) -> dict:
    items = action_repository.fetch_designer_actions(
        db, client_id, environment=environment,
        capability=capability, category=category, search_query=search_query,
    )
    return {"items": items, "total": len(items)}


def get_action_by_id(db: Session, action_definition_id: str) -> dict | None:
    return action_repository.fetch_action_by_id(db, action_definition_id)


def update_action_definition(db: Session, action_definition_id: str, request) -> dict:
    result = action_repository.update_action_definition(db, action_definition_id, request)
    logger.info(f"Updated action definition '{action_definition_id}'")
    return result


def update_action_version(db: Session, action_version_id: str, request) -> dict:
    result = action_repository.update_action_version(db, action_version_id, request)
    logger.info(f"Updated action version '{action_version_id}'")
    return result


def publish_action_version(db: Session, action_version_id: str, release_notes: str | None = None) -> dict:
    result = action_repository.publish_action_version(db, action_version_id, release_notes)
    logger.info(f"Published action version '{action_version_id}' as v{result['version']}")
    return result


def create_draft_from_published(db: Session, from_version_id: str, user_id: str) -> dict:
    result = action_repository.create_draft_from_published(db, from_version_id, user_id)
    logger.info(f"Created draft v{result['version']} from version '{from_version_id}'")
    return result
