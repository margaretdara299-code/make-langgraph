"""
Action controller — 4 API routes only. No versioning.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db_session
from app.common.response import build_success_response, raise_internal_server_error, raise_not_found, raise_bad_request
from app.action.models import CreateActionDefinitionRequest, UpdateActionDefinitionRequest, UpdateActionStatusRequest
from app.action import service as action_service
from app.logger.logging import logger

router = APIRouter(prefix="/actions", tags=["Actions"])
designer_router = APIRouter(prefix="/designer", tags=["Designer"])


@router.post("", status_code=201)
def create_action(
    request: CreateActionDefinitionRequest,
    db: Session = Depends(get_db_session),
):
    """Create a new action. Default: status=published, is_active=true."""
    logger.debug(f"Creating action: {request.name}")
    try:
        result = action_service.create_action(db, request, 1)
        return build_success_response("Action created", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error creating action")
        raise_internal_server_error()


@router.get("")
def list_actions(
    db: Session = Depends(get_db_session),
    status: str | None = Query(default=None),
    capability: int | None = Query(default=None),
    category: int | None = Query(default=None),
    q: str | None = Query(default=None),
):
    """List all actions. Optional filters: status, capability, category, q (search)."""
    logger.debug("Fetching actions list")
    try:
        result = action_service.list_actions(db, status=status, capability_id=capability,
                                              category_id=category, search_query=q)
        return build_success_response("Actions fetched", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error fetching actions")
        raise_internal_server_error()


@router.get("/grouped")
def list_actions_grouped(
    db: Session = Depends(get_db_session)
):
    """List actions grouped by their category name."""
    logger.debug("Fetching actions grouped by category")
    try:
        result = action_service.list_actions_grouped(db)
        return build_success_response("Grouped actions fetched", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error fetching grouped actions")
        raise_internal_server_error()


@router.put("/{action_definition_id}/status")
def update_action_status(
    action_definition_id: int,
    request: UpdateActionStatusRequest,
    db: Session = Depends(get_db_session)
):
    """Update only the status (draft/published) and/or is_active flag."""
    logger.debug(f"Updating status for action: {action_definition_id}")
    try:
        result = action_service.update_action_status(db, action_definition_id, request)
        return build_success_response("Action status updated", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error updating action status")
        raise_internal_server_error()


@router.get("/{action_definition_id}")
def get_action(
    action_definition_id: int,
    db: Session = Depends(get_db_session),
):
    """Get a single action with all its JSON blobs."""
    logger.debug(f"Fetching action: {action_definition_id}")
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


@router.put("/{action_definition_id}")
def update_action(
    action_definition_id: int,
    request: UpdateActionDefinitionRequest,
    db: Session = Depends(get_db_session),
):
    """Update action metadata and/or JSON blobs. Also supports status and is_active."""
    logger.debug(f"Updating action: {action_definition_id}")
    try:
        result = action_service.update_action(db, action_definition_id, request)
        return build_success_response("Action updated", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error updating action")
        raise_internal_server_error()


@router.delete("/{action_definition_id}")
def delete_action(
    action_definition_id: int,
    db: Session = Depends(get_db_session)
):
    """Delete an action (only if not in use by any skill graphs)."""
    logger.debug(f"Deleting action: {action_definition_id}")
    try:
        success = action_service.delete_action(db, action_definition_id)
        if not success:
            raise_bad_request("Action cannot be deleted: it is currently referenced in one or more skill graphs.")
            
        return build_success_response("Action deleted successfully", {"action_definition_id": action_definition_id})
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Error deleting action {action_definition_id}")
        raise_internal_server_error()

