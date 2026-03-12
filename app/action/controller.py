"""
Action controller — API routes for the Action Catalog and designer left rail.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db_session
from app.common.response import build_success_response, raise_internal_server_error, raise_not_found
from app.models.action import (
    CreateActionDefinitionRequest,
    UpdateActionVersionRequest,
    PublishActionRequest,
    CreateDraftFromPublishedRequest,
)
from app.action import service as action_service
from app.logger.logging import logger

router = APIRouter(prefix="/api", tags=["Actions"])


# =========================================================================
# Action Definition CRUD
# =========================================================================

@router.get("/actions")
def list_all_actions(
    db: Session = Depends(get_db_session),
    status: str | None = Query(default=None),
    capability: str | None = Query(default=None),
    category: str | None = Query(default=None),
    search_query: str | None = Query(default=None, alias="q"),
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


@router.get("/actions/{action_definition_id}")
def get_action_by_id(
    action_definition_id: str,
    db: Session = Depends(get_db_session),
):
    """Return a single action definition with all its versions."""
    logger.info(f"Fetching action: {action_definition_id}")
    try:
        result = action_service.get_action_by_id(db, action_definition_id)
        if not result:
            raise_not_found("Action not found")
        return build_success_response("Action fetched", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error fetching action")
        raise_internal_server_error()


# =========================================================================
# Action Version Management
# =========================================================================

@router.put("/actions/versions/{action_version_id}")
def update_action_version(
    action_version_id: str,
    request: UpdateActionVersionRequest,
    db: Session = Depends(get_db_session),
):
    """Update a draft action version's JSON schemas."""
    logger.info(f"Updating action version: {action_version_id}")
    try:
        result = action_service.update_action_version(db, action_version_id, request)
        return build_success_response("Action version updated", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error updating action version")
        raise_internal_server_error()


@router.post("/actions/versions/{action_version_id}/publish")
def publish_action_version(
    action_version_id: str,
    request: PublishActionRequest = PublishActionRequest(),
    db: Session = Depends(get_db_session),
):
    """Publish a draft action version (draft → published + active)."""
    logger.info(f"Publishing action version: {action_version_id}")
    try:
        result = action_service.publish_action_version(db, action_version_id, request.release_notes)
        return build_success_response("Action version published", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error publishing action version")
        raise_internal_server_error()


@router.post("/actions/versions/draft-from", status_code=201)
def create_draft_from_published(
    request: CreateDraftFromPublishedRequest,
    db: Session = Depends(get_db_session),
):
    """Create a new draft version by cloning a published version."""
    logger.info(f"Creating draft from version: {request.from_version_id}")
    try:
        result = action_service.create_draft_from_published(db, request.from_version_id, "system")
        return build_success_response("Draft version created", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error creating draft from published")
        raise_internal_server_error()


# =========================================================================
# Designer Left Rail
# =========================================================================

@router.get("/designer/actions")
def get_designer_actions(
    db: Session = Depends(get_db_session),
    client_id: str = Query(default="c_demo"),
    environment: str = Query(default="dev"),
    capability: str | None = Query(default=None),
    category: str | None = Query(default=None),
    search_query: str | None = Query(default=None, alias="q"),
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
