"""
Skill controller — API routes for the Skills Library.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db_session
from app.common.response import build_success_response, raise_internal_server_error
from app.models.skill import CreateSkillRequest
from app.skill import service as skill_service
from app.skill import repository as skill_repository
from app.logger.logging import logger

router = APIRouter(prefix="/api", tags=["Skills"])


@router.get("/skills")
def list_all_skills(
    db: Session = Depends(get_db_session),
    client_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    search_query: Optional[str] = Query(default=None, alias="search"),
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
