"""
Skill controller — API routes for Skills Library and Visual Skill Designer.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db_session
from app.common.response import build_success_response, raise_internal_server_error, raise_not_found
from app.skill.models import (CreateSkillRequest, UpdateSkillRequest, 
                               SaveSkillGraphRequest, UpdateNodeConfigRequest,
                               UpdateSkillVersionStatusRequest, RunSkillRequest)
from app.skill import service as skill_service
from app.logger.logging import logger

router = APIRouter(prefix="/skills", tags=["Skills"])
version_router = APIRouter(prefix="/skill-versions", tags=["Skill Versions"])

# =========================================================================
# Skills Library (Metadata CRUD)
# =========================================================================

@router.get("")
def list_all_skills(
    db: Session = Depends(get_db_session),
    client_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    search_query: str | None = Query(default=None, alias="search"),
):
    logger.debug("Fetching skills list")
    try:
        result = skill_service.list_all_skills(db, client_id=client_id, status=status, search_query=search_query)
        return build_success_response("Skills fetched", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error fetching skills list")
        raise_internal_server_error()


@router.post("", status_code=201)
def create_skill(
    request: CreateSkillRequest,
    db: Session = Depends(get_db_session),
):
    logger.debug(f"Creating skill: {request.name}")
    try:
        result = skill_service.create_skill(db, request, 1)
        return build_success_response("Skill created", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error creating skill")
        raise_internal_server_error()


@router.get("/{skill_id}")
def get_skill(
    skill_id: int,
    db: Session = Depends(get_db_session),
):
    """Fetch a single skill's full metadata."""
    logger.debug(f"Fetching skill: {skill_id}")
    try:
        result = skill_service.get_skill(db, skill_id)
        if not result:
            raise_not_found("Skill not found")
        return build_success_response("Skill fetched", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Error fetching skill {skill_id}")
        raise_internal_server_error()


@router.patch("/{skill_id}")
def update_skill(
    skill_id: int,
    request: UpdateSkillRequest,
    db: Session = Depends(get_db_session),
):
    """Update skill metadata."""
    logger.debug(f"Updating skill: {skill_id}")
    try:
        success = skill_service.update_skill(db, skill_id, request)
        if not success:
            raise_not_found("Skill not found")
        return build_success_response("Skill updated", {"id": skill_id})
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Error updating skill {skill_id}")
        raise_internal_server_error()


@router.delete("/{skill_id}")
def delete_skill(
    skill_id: int,
    db: Session = Depends(get_db_session),
):
    """Delete a skill and all its versions."""
    logger.debug(f"Deleting skill: {skill_id}")
    try:
        success = skill_service.delete_skill(db, skill_id)
        if not success:
            raise_not_found("Skill not found")
        return build_success_response("Skill deleted", {"id": skill_id})
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Error deleting skill {skill_id}")
        raise_internal_server_error()


# =========================================================================
# Visual Designer (Graph Lifecycle)
# =========================================================================

@version_router.get("/{skill_version_id}/graph")
def load_skill_graph(
    skill_version_id: int, 
    db: Session = Depends(get_db_session)
):
    """Load the current workflow graph (nodes + connections) for a skill version."""
    logger.debug(f"Loading graph for version: {skill_version_id}")
    try:
        result = skill_service.get_skill_graph(db, skill_version_id)
        return build_success_response("Graph loaded", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error loading graph")
        raise_internal_server_error()


@version_router.get("/{skill_version_id}")
def get_skill_version_detail(
    skill_version_id: int, 
    db: Session = Depends(get_db_session)
):
    """Alias to load graph and version metadata."""
    try:
        result = skill_service.get_skill_graph(db, skill_version_id)
        return build_success_response("Skill version loaded", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error loading skill version")
        raise_internal_server_error()


@version_router.put("/{skill_version_id}/graph")
def save_skill_graph(
    skill_version_id: int, 
    request: SaveSkillGraphRequest, 
    db: Session = Depends(get_db_session)
):
    """Bulk-save nodes and connections for a skill version."""
    logger.debug(f"Saving graph for version: {skill_version_id}")
    try:
        result = skill_service.save_graph(db, skill_version_id, request)
        return build_success_response("Graph saved", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error saving graph")
        raise_internal_server_error()


@version_router.patch("/{skill_version_id}/nodes/{node_id}/data")
def update_node_data(
    skill_version_id: int, 
    node_id: str, 
    request: UpdateNodeConfigRequest,
    db: Session = Depends(get_db_session)
):
    """Update a single node's configuration data."""
    try:
        skill_service.update_node(db, skill_version_id, node_id, request.data)
        return build_success_response("Node updated")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error updating node data")
        raise_internal_server_error()


@version_router.put("/{skill_version_id}/status")
def update_skill_version_status(
    skill_version_id: int, 
    request: UpdateSkillVersionStatusRequest,
    db: Session = Depends(get_db_session)
):
    """Unified endpoint to publish or unpublish a skill version."""
    logger.debug(f"Updating skill version status: {skill_version_id} -> {request.status}")
    try:
        result = skill_service.update_skill_version_status(db, skill_version_id, request)
        
        messages = {
            "published": "Published successfully",
            "unpublished": "Unpublished successfully",
            "draft": "Reverted to draft successfully"
        }
        message = messages.get(request.status, "Status updated successfully")
        
        return build_success_response(message, None)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error updating version status")
        raise_internal_server_error()


@version_router.post("/{skill_version_id}/validate")
def validate_skill_version(
    skill_version_id: int,
    db: Session = Depends(get_db_session)
):
    """Run engine validation on a saved skill version."""
    try:
        result = skill_service.validate_skill_version(db, skill_version_id)
        return build_success_response("Validation complete", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Error validating version {skill_version_id}")
        raise_internal_server_error()


@version_router.post("/{skill_version_id}/compile")
def compile_skill_version(
    skill_version_id: int,
    db: Session = Depends(get_db_session)
):
    """Compile a skill version into an execution plan."""
    try:
        result = skill_service.compile_skill_version(db, skill_version_id)
        return build_success_response("Compilation complete", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Error compiling version {skill_version_id}")
        raise_internal_server_error()


@version_router.post("/{skill_version_id}/run")
def run_skill_version(
    skill_version_id: int,
    request: RunSkillRequest,
    db: Session = Depends(get_db_session)
):
    """Execute a skill version (dry-run)."""
    try:
        result = skill_service.run_skill_version(db, skill_version_id, request.input_context)
        return build_success_response("Execution complete", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Error running version {skill_version_id}")
        raise_internal_server_error()


