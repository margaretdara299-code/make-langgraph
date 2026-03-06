"""
Action controller — API routes for the Action Catalog and designer left rail.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db_session
from app.common.response import build_success_response, raise_internal_server_error
from app.models.action import CreateActionDefinitionRequest
from app.action import service as action_service
from app.logger.logging import logger

router = APIRouter(prefix="/api", tags=["Actions"])


@router.get("/actions")
def list_all_actions(
    db: Session = Depends(get_db_session),
    status: Optional[str] = Query(default=None),
    capability: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    search_query: Optional[str] = Query(default=None, alias="q"),
):
    logger.info("Fetching actions list")
    try:
        result = action_service.list_all_actions(db, status=status, capability=capability,
                                                  category=category, search_query=search_query)
        return build_success_response("Actions fetched", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error fetching actions list")
        raise_internal_server_error()


@router.post("/actions", status_code=201)
def create_action(
    request: CreateActionDefinitionRequest,
    db: Session = Depends(get_db_session),
):
    logger.info(f"Creating action: {request.name}")
    try:
        result = action_service.create_action_definition(db, request, "system")
        return build_success_response("Action created", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error creating action")
        raise_internal_server_error()


@router.get("/designer/actions")
def get_designer_actions(
    db: Session = Depends(get_db_session),
    client_id: str = Query(default="c_demo"),
    environment: str = Query(default="dev"),
    capability: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    search_query: Optional[str] = Query(default=None, alias="q"),
):
    """Return published actions for the Designer left-rail."""
    logger.info(f"Fetching designer actions for client={client_id}, env={environment}")
    try:
        result = action_service.get_designer_actions(
            db, client_id, environment=environment,
            capability=capability, category=category, search_query=search_query,
        )
        return build_success_response("Designer actions fetched", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error fetching designer actions")
        raise_internal_server_error()
