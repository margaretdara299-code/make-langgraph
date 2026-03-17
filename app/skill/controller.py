"""
Skill controller — API routes for the Skills Library.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db_session
from app.common.response import build_success_response, raise_internal_server_error, raise_not_found
from app.models.skill import CreateSkillRequest, SaveSkillGraphRequest, UpdateNodeConfigRequest
from app.skill import service as skill_service
from app.skill import repository as skill_repository
from app.logger.logging import logger

router = APIRouter(prefix="/api", tags=["Skills"])


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


@router.get("/skills/suggest-key")
def suggest_skill_key(
    db: Session = Depends(get_db_session),
    client_id: str = Query(...),
    name: str = Query(...),
):
    suggested = skill_repository.suggest_skill_key(db, client_id, name)
    return build_success_response("Key suggested", {"suggested_skill_key": suggested})


# =========================================================================
# Graph Endpoints (per skill version)
# =========================================================================

@router.get("/skills/versions/{skill_version_id}/graph")
def get_skill_graph(
    skill_version_id: str,
    db: Session = Depends(get_db_session),
):
    """Load the current workflow graph (nodes + connections) for a skill version."""
    logger.info(f"Fetching graph for version: {skill_version_id}")
    try:
        result = skill_service.get_skill_graph(db, skill_version_id)
        if not result:
            raise_not_found("Skill version not found")
        return build_success_response("Graph fetched", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error fetching skill graph")
        raise_internal_server_error()


@router.put("/skills/versions/{skill_version_id}/graph")
def save_skill_graph(
    skill_version_id: str,
    request: SaveSkillGraphRequest,
    db: Session = Depends(get_db_session),
):
    """Bulk-save the entire workflow graph (nodes + connections) for a skill version."""
    logger.info(f"Saving graph for version: {skill_version_id}")
    try:
        # Verify version exists
        version = skill_repository.fetch_skill_version_by_id(db, skill_version_id)
        if not version:
            raise_not_found("Skill version not found")

        nodes = [n.model_dump() for n in request.nodes]
        connections = {k: v.model_dump() for k, v in request.connections.items()}

        result = skill_service.save_graph(db, skill_version_id, nodes, connections)
        return build_success_response("Graph saved", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error saving skill graph")
        raise_internal_server_error()


@router.patch("/skills/versions/{skill_version_id}/nodes/{node_id}")
def update_node(
    skill_version_id: str,
    node_id: str,
    request: UpdateNodeConfigRequest,
    db: Session = Depends(get_db_session),
):
    """Update a single node's configuration data (from the right-panel form)."""
    logger.info(f"Updating node '{node_id}' in version: {skill_version_id}")
    try:
        result = skill_service.update_node(db, skill_version_id, node_id, request.data)
        if not result:
            raise_not_found("Skill version or node not found")
        return build_success_response("Node updated", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error updating node")
        raise_internal_server_error()
