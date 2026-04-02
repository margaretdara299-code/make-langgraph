"""
Engine controller — API routes for the Workflow Execution Engine.
"""
from fastapi import APIRouter, HTTPException, Body, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any
from sqlalchemy.orm import Session
from app.core.database import get_db_session as get_db
from app.skill.repository import fetch_skill_graph
from app.common.response import build_success_response, raise_internal_server_error
from app.engine.codegen.generator import generate_project_files
from app.engine.executor.runner import run_workflow
from app.logger.logging import logger

router = APIRouter(prefix="/engine", tags=["Workflow Engine"])

# ── Request models ─────────────────────────────────────────────────────
class WorkflowPayload(BaseModel):
    """Payload containing a workflow JSON definition, or a compiled plan."""
    nodes: list[dict[str, Any]] | None = None
    edges: list[dict[str, Any]] | None = None
    compile_hash: str | None = None
    workflow_json: dict[str, Any] | None = None
    skill_version_id: str | None = None


# =========================================================================
# Dashboard / Summary counts
# =========================================================================

@router.get("/counts")
def get_engine_counts(db: Session = Depends(get_db)):
    """Return an aggregated count of all skills and actions based on status and active state."""
    logger.debug("Engine: retrieving system counts")
    from sqlalchemy import text
    try:
        # Action Counts
        actions = db.execute(text("""
            SELECT is_active, status, COUNT(*) as cnt 
            FROM action_definition 
            GROUP BY is_active, status
        """)).mappings().all()

        action_total = sum(row['cnt'] for row in actions)
        action_active = sum(row['cnt'] for row in actions if row['is_active'] == 1)
        action_inactive = sum(row['cnt'] for row in actions if row['is_active'] == 0)
        action_published = sum(row['cnt'] for row in actions if row['status'] == 'published')
        action_draft = sum(row['cnt'] for row in actions if row['status'] == 'draft')

        # Skill Counts
        skills = db.execute(text("""
            SELECT is_active, COUNT(*) as cnt 
            FROM skill 
            GROUP BY is_active
        """)).mappings().all()

        skill_total = sum(row['cnt'] for row in skills)
        skill_active = sum(row['cnt'] for row in skills if row['is_active'] == 1)
        skill_inactive = sum(row['cnt'] for row in skills if row['is_active'] == 0)

        # Skill Version Counts (for status)
        skill_versions = db.execute(text("""
            SELECT status, COUNT(*) as cnt 
            FROM skill_version 
            GROUP BY status
        """)).mappings().all()
        
        sv_published = sum(row['cnt'] for row in skill_versions if row['status'] == 'published')
        sv_draft = sum(row['cnt'] for row in skill_versions if row['status'] == 'draft')

        data = {
            "actions": {
                "total": action_total,
                "active": action_active,
                "inactive": action_inactive,
                "published": action_published,
                "draft": action_draft
            },
            "skills": {
                "total": skill_total,
                "active": skill_active,
                "inactive": skill_inactive,
                "published_versions": sv_published,
                "draft_versions": sv_draft
            }
        }

        return build_success_response("System counts retrieved", data)
    except Exception:
        logger.exception("Error retrieving system counts")
        raise_internal_server_error()

@router.get("/generate-code/{skill_version_id}")
def generate_workflow_code_by_id(
    skill_version_id: str,
    db: Session = Depends(get_db)
):
    """Fetch a workflow from DB and generate a complete multi-file LangGraph project."""
    logger.debug(f"Engine: generating project files for skill version {skill_version_id}")
    try:
        skill_graph = fetch_skill_graph(db, skill_version_id)
        workflow_data = {
            "nodes": [n.model_dump() for n in skill_graph.nodes],
            "connections": {k: v.model_dump() for k, v in skill_graph.connections.items()}
        }
        files = generate_project_files(
            workflow_data,
            workflow_name=f"Skill Version {skill_version_id}"
        )
        return build_success_response("Project files generated successfully", files)
    except Exception:
        logger.exception(f"Error generating project files for {skill_version_id}")
        raise_internal_server_error()

@router.post("/run/{skill_version_id}")
def run_workflow_by_id(
    skill_version_id: str,
    db: Session = Depends(get_db)
):
    """Fetch a workflow from DB, compile it using LangGraph, and execute it."""
    logger.debug(f"Engine: running workflow for version {skill_version_id}")
    try:
        skill_graph = fetch_skill_graph(db, skill_version_id)
        workflow_data = {
            "nodes": [n.model_dump() for n in skill_graph.nodes],
            "connections": {k: v.model_dump() for k, v in skill_graph.connections.items()}
        }
        
        # Execute workflow synchronously returning the final dictionary state
        # A thread suffix _api ensures checkpointing works properly across API calls
        final_state = run_workflow(workflow_data, thread_id=f"api_{skill_version_id}")
        
        return build_success_response("Workflow executed successfully", final_state)
    except ValueError as ve:
        logger.warning(f"Workflow compilation failed for {skill_version_id}: {ve}")
        return JSONResponse(status_code=400, content={"status": False, "message": str(ve), "data": None})
    except Exception as e:
        logger.exception(f"Error executing workflow for {skill_version_id}")
        return raise_internal_server_error()
