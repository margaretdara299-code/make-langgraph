"""
Action service — business logic for the Action Catalog.
"""
from sqlalchemy.orm import Session
from app.action import repository as repo
from app.logger.logging import logger


def create_action(db: Session, request, user_id: str) -> dict:
    result = repo.insert_action(db, request, user_id)
    logger.info(f"Created action '{request.name}' (key={request.action_key})")
    return result


def list_actions(db: Session, status: str | None = None, capability: str | None = None,
                 category: str | None = None, search_query: str | None = None) -> dict:
    items = repo.fetch_all_actions(db, status=status, capability_id=capability,
                                   category_id=category, search_query=search_query)
    return {"items": items, "total": len(items)}


def get_action_by_id(db: Session, action_definition_id: str) -> dict | None:
    return repo.fetch_action_by_id(db, action_definition_id)


def update_action(db: Session, action_definition_id: str, request) -> dict:
    result = repo.update_action(db, action_definition_id, request)
    logger.info(f"Updated action '{action_definition_id}'")
    return result


def update_action_status(db: Session, action_definition_id: str, request) -> dict:
    result = repo.update_action_status(db, action_definition_id, request)
    logger.info(f"Updated status for action '{action_definition_id}'")
    return result
