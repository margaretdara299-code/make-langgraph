"""
Action service — business logic for the Action Catalog.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.action import repository as action_repository
from app.logger.logging import logger


def list_all_actions(db: Session, status: Optional[str] = None, capability: Optional[str] = None,
                     category: Optional[str] = None, search_query: Optional[str] = None) -> dict:
    items = action_repository.fetch_all_actions(db, status=status, capability=capability,
                                                 category=category, search_query=search_query)
    return {"items": items, "total": len(items)}


def create_action_definition(db: Session, request, user_id: str) -> dict:
    result = action_repository.insert_action_definition(db, request, user_id)
    logger.info(f"Created action '{request.name}' (key={request.action_key})")
    return result


def get_designer_actions(db: Session, client_id: str, environment: str = "dev",
                         capability: Optional[str] = None, category: Optional[str] = None,
                         search_query: Optional[str] = None) -> dict:
    items = action_repository.fetch_designer_actions(
        db, client_id, environment=environment,
        capability=capability, category=category, search_query=search_query,
    )
    return {"items": items, "total": len(items)}
