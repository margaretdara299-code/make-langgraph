"""
Skill controller — API routes for Skills Library and Visual Skill Designer.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db_session
from app.common.response import build_success_response, raise_internal_server_error, raise_not_found
from app.models.skill import (CreateSkillRequest, UpdateSkillRequest, 
                               SaveSkillGraphRequest, UpdateNodeConfigRequest,
                               PublishSkillRequest, RunSkillRequest)
from app.skill import service as skill_service
from app.logger.logging import logger

router = APIRouter(prefix="/api", tags=["Skills"])


# =========================================================================
# Skills Library (Metadata CRUD)
# =========================================================================

@router.get("/skills")
def list_all_skills(
    db: Session = Depends(get_db_session),
    client_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    search_query: str | None = Query(default=None, alias="search"),
):
    logger.info("Fetching skills list")
    try:
        result = skill_service.list_all_skills(db, client_id=client_id, status=status, search_query=search_query)
        return build_success_response("Skills fetched", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error fetching skills list")
        raise_internal_server_error()


@router.post("/skills", status_code=201)
def create_skill(
    request: CreateSkillRequest,
    db: Session = Depends(get_db_session),
):
    logger.info(f"Creating skill: {request.name}")
    try:
        result = skill_service.create_skill(db, request, "system")
        return build_success_response("Skill created", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error creating skill")
        raise_internal_server_error()


@router.get("/skills/{skill_id}")
def get_skill(
    skill_id: str,
    db: Session = Depends(get_db_session),
):
    """Fetch a single skill's full metadata."""
    logger.info(f"Fetching skill: {skill_id}")
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


@router.patch("/skills/{skill_id}")
def update_skill(
    skill_id: str,
    request: UpdateSkillRequest,
    db: Session = Depends(get_db_session),
):
    """Update skill metadata."""
    logger.info(f"Updating skill: {skill_id}")
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


@router.delete("/skills/{skill_id}")
def delete_skill(
    skill_id: str,
    db: Session = Depends(get_db_session),
):
    """Delete a skill and all its versions."""
    logger.info(f"Deleting skill: {skill_id}")
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

@router.get("/skills/versions/{skill_version_id}/graph")
def load_skill_graph(
    skill_version_id: str, 
    db: Session = Depends(get_db_session)
):
    """Load the current workflow graph (nodes + connections) for a skill version."""
    logger.info(f"Loading graph for version: {skill_version_id}")
    try:
        result = skill_service.get_skill_graph(db, skill_version_id)
        return build_success_response("Graph loaded", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error loading graph")
        raise_internal_server_error()


@router.get("/skills/versions/{skill_version_id}")
def get_skill_version_detail(
    skill_version_id: str, 
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


@router.put("/skills/versions/{skill_version_id}/graph")
def save_skill_graph(
    skill_version_id: str, 
    request: SaveSkillGraphRequest, 
    db: Session = Depends(get_db_session)
):
    """Bulk-save nodes and connections for a skill version."""
    logger.info(f"Saving graph for version: {skill_version_id}")
    try:
        result = skill_service.save_graph(db, skill_version_id, request)
        return build_success_response("Graph saved", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error saving graph")
        raise_internal_server_error()


@router.patch("/skills/versions/{skill_version_id}/nodes/{node_id}/data")
def update_node_data(
    skill_version_id: str, 
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


@router.post("/skills/versions/{skill_version_id}/validate")
def validate_skill_version(
    skill_version_id: str, 
    db: Session = Depends(get_db_session)
):
    """Run server-side validation on the skill graph."""
    try:
        result = skill_service.validate_graph(db, skill_version_id)
        return build_success_response("Validation complete", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error validating graph")
        raise_internal_server_error()


@router.post("/skills/versions/{skill_version_id}/compile")
def compile_skill_version(
    skill_version_id: str, 
    db: Session = Depends(get_db_session)
):
    """Compile the graph into a runnable JSON format (LangGraph style)."""
    logger.info(f"Compiling skill version: {skill_version_id}")
    try:
        result = skill_service.compile_graph(db, skill_version_id)
        return build_success_response("Compiled successfully", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error compiling graph")
        raise_internal_server_error()


@router.post("/skills/versions/{skill_version_id}/publish")
def publish_skill_version(
    skill_version_id: str, 
    request: PublishSkillRequest = None, 
    db: Session = Depends(get_db_session)
):
    """Mark a compiled draft as published and active for the environment."""
    logger.info(f"Publishing skill version: {skill_version_id}")
    try:
        notes = request.notes if request else None
        result = skill_service.publish_skill_version(db, skill_version_id, notes)
        return build_success_response("Published successfully", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error publishing version")
        raise_internal_server_error()


@router.post("/skills/versions/{skill_version_id}/run")
def run_skill_version(
    skill_version_id: str, 
    request: RunSkillRequest, 
    db: Session = Depends(get_db_session)
):
    """Execute the compiled skill logic locally for testing."""
    try:
        result = skill_service.run_skill(db, skill_version_id, request)
        return build_success_response("Run complete", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error running skill")
        raise_internal_server_error()
