"""
Skill graph controller — API routes for the Visual Skill Designer.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db_session
from app.common.response import build_success_response, raise_internal_server_error
from app.models.skill import (PublishSkillRequest, RunSkillRequest,
                               SaveSkillGraphRequest, UpdateNodeConfigRequest)
from app.skill_graph import service as graph_service
from app.logger.logging import logger

router = APIRouter(prefix="/api", tags=["Skill Graph"])


# ── Load graph ──
@router.get("/skill-versions/{skill_version_id}/graph")
def load_skill_version_graph(skill_version_id: str, db: Session = Depends(get_db_session)):
    logger.info(f"Loading graph for version: {skill_version_id}")
    try:
        result = graph_service.get_graph(db, skill_version_id)
        return build_success_response("Graph loaded", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error loading graph")
        raise_internal_server_error()


# ── Alias GET ──
@router.get("/skill-versions/{skill_version_id}")
def get_skill_version(skill_version_id: str, db: Session = Depends(get_db_session)):
    try:
        result = graph_service.get_graph(db, skill_version_id)
        return build_success_response("Skill version loaded", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error loading skill version")
        raise_internal_server_error()


# ── Save graph ──
@router.put("/skill-versions/{skill_version_id}/graph")
def save_skill_version_graph(skill_version_id: str, request: SaveSkillGraphRequest, db: Session = Depends(get_db_session)):
    logger.info(f"Saving graph for version: {skill_version_id}")
    try:
        result = graph_service.save_graph(db, skill_version_id, request)
        return build_success_response("Graph saved", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error saving graph")
        raise_internal_server_error()


# ── Update node data (PATCH) ──
@router.patch("/skill-versions/{skill_version_id}/nodes/{node_id}/data")
def update_node_data_patch(skill_version_id: str, node_id: str, request: UpdateNodeConfigRequest, db: Session = Depends(get_db_session)):
    try:
        graph_service.update_node_data(db, skill_version_id, node_id, request.data)
        return build_success_response("Node updated")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error updating node data")
        raise_internal_server_error()


# ── Update node data (PUT) ──
@router.put("/skill-versions/{skill_version_id}/nodes/{node_id}/data")
def update_node_data_put(skill_version_id: str, node_id: str, request: UpdateNodeConfigRequest, db: Session = Depends(get_db_session)):
    try:
        graph_service.update_node_data(db, skill_version_id, node_id, request.data)
        return build_success_response("Node updated")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error updating node data")
        raise_internal_server_error()


# ── Validate ──
@router.post("/skill-versions/{skill_version_id}/validate")
def validate_skill_version(skill_version_id: str, db: Session = Depends(get_db_session)):
    try:
        result = graph_service.validate_graph(db, skill_version_id)
        return build_success_response("Validation complete", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error validating graph")
        raise_internal_server_error()


# ── Compile ──
@router.post("/skill-versions/{skill_version_id}/compile")
def compile_skill_version(skill_version_id: str, db: Session = Depends(get_db_session)):
    logger.info(f"Compiling skill version: {skill_version_id}")
    try:
        result = graph_service.compile_graph(db, skill_version_id)
        return build_success_response("Compiled successfully", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error compiling graph")
        raise_internal_server_error()


# ── Publish ──
@router.post("/skill-versions/{skill_version_id}/publish")
def publish_skill_version(skill_version_id: str, request: PublishSkillRequest = None, db: Session = Depends(get_db_session)):
    logger.info(f"Publishing skill version: {skill_version_id}")
    try:
        notes = request.notes if request else None
        result = graph_service.publish_skill_version(db, skill_version_id, notes)
        return build_success_response("Published successfully", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error publishing version")
        raise_internal_server_error()


# ── Run ──
@router.post("/skill-versions/{skill_version_id}/run")
def run_skill_version(skill_version_id: str, request: RunSkillRequest, db: Session = Depends(get_db_session)):
    try:
        result = graph_service.run_skill(db, skill_version_id, request)
        return build_success_response("Run complete", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error running skill")
        raise_internal_server_error()
