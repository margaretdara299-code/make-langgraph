"""
Skill graph controller — API routes for the Visual Skill Designer.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db_session
from app.common.response import ok, internal_error
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
        return ok(result, "Graph loaded")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error loading graph")
        internal_error()


# ── Alias GET ──
@router.get("/skill-versions/{skill_version_id}")
def get_skill_version(skill_version_id: str, db: Session = Depends(get_db_session)):
    try:
        result = graph_service.get_graph(db, skill_version_id)
        return ok(result, "Skill version loaded")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error loading skill version")
        internal_error()


# ── Save graph ──
@router.put("/skill-versions/{skill_version_id}/graph")
def save_skill_version_graph(skill_version_id: str, request: SaveSkillGraphRequest, db: Session = Depends(get_db_session)):
    logger.info(f"Saving graph for version: {skill_version_id}")
    try:
        result = graph_service.save_graph(db, skill_version_id, request)
        return ok(result, "Graph saved")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error saving graph")
        internal_error()


# ── Update node data (PATCH) ──
@router.patch("/skill-versions/{skill_version_id}/nodes/{node_id}/data")
def update_node_data_patch(skill_version_id: str, node_id: str, request: UpdateNodeConfigRequest, db: Session = Depends(get_db_session)):
    try:
        graph_service.update_node_data(db, skill_version_id, node_id, request.data)
        return ok(message="Node updated")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error updating node data")
        internal_error()


# ── Update node data (PUT) ──
@router.put("/skill-versions/{skill_version_id}/nodes/{node_id}/data")
def update_node_data_put(skill_version_id: str, node_id: str, request: UpdateNodeConfigRequest, db: Session = Depends(get_db_session)):
    try:
        graph_service.update_node_data(db, skill_version_id, node_id, request.data)
        return ok(message="Node updated")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error updating node data")
        internal_error()


# ── Validate ──
@router.post("/skill-versions/{skill_version_id}/validate")
def validate_skill_version(skill_version_id: str, db: Session = Depends(get_db_session)):
    try:
        result = graph_service.validate_graph(db, skill_version_id)
        return ok(result, "Validation complete")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error validating graph")
        internal_error()


# ── Compile ──
@router.post("/skill-versions/{skill_version_id}/compile")
def compile_skill_version(skill_version_id: str, db: Session = Depends(get_db_session)):
    logger.info(f"Compiling skill version: {skill_version_id}")
    try:
        result = graph_service.compile_graph(db, skill_version_id)
        return ok(result, "Compiled successfully")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error compiling graph")
        internal_error()


# ── Publish ──
@router.post("/skill-versions/{skill_version_id}/publish")
def publish_skill_version(skill_version_id: str, request: PublishSkillRequest = None, db: Session = Depends(get_db_session)):
    logger.info(f"Publishing skill version: {skill_version_id}")
    try:
        notes = request.notes if request else None
        result = graph_service.publish_skill_version(db, skill_version_id, notes)
        return ok(result, "Published successfully")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error publishing version")
        internal_error()


# ── Run ──
@router.post("/skill-versions/{skill_version_id}/run")
def run_skill_version(skill_version_id: str, request: RunSkillRequest, db: Session = Depends(get_db_session)):
    try:
        result = graph_service.run_skill(db, skill_version_id, request)
        return ok(result, "Run complete")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error running skill")
        internal_error()
