"""
Engine controller — API routes for the Workflow Execution Engine.
"""
from fastapi import APIRouter, HTTPException, Body, Depends
from pydantic import BaseModel
from typing import Any
from sqlalchemy.orm import Session
from app.core.database import get_db_session as get_db
from app.skill.repository import fetch_skill_graph
from app.common.response import build_success_response, raise_internal_server_error, raise_bad_request
from app.engine.runner import run_workflow
from app.engine.validator import validate_workflow
from app.engine.graph_builder import compile_workflow_plan
from app.engine.codegen import generate_langgraph_source
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


# =========================================================================
# Validate a workflow
# =========================================================================

@router.post("/validate")
def validate_engine_workflow(request: dict = Body(...)):
    """Run structural checks on a workflow JSON definition without building it."""
    try:
        result = validate_workflow(request)
        return build_success_response("Validation complete", result)
    except Exception:
        logger.exception("Error validating workflow")
        raise_internal_server_error()


# =========================================================================
# Compile a workflow
# =========================================================================

@router.post("/compile")
def compile_engine_workflow(request: dict = Body(...)):
    """Validate and hash the workflow definition into a cacheable execution plan."""
    try:
        plan = compile_workflow_plan(request)
        return build_success_response("Workflow compiled successfully", plan)
    except ValueError as e:
        raise_bad_request(str(e))
    except Exception:
        logger.exception("Error compiling workflow")
        raise_internal_server_error()


# =========================================================================
# Execute a workflow
# =========================================================================

@router.post("/run", status_code=200)
def execute_workflow(
    request: dict = Body(...),
    thread_id: str = "default_session"
):
    """
    Execute a workflow JSON or compiled plan.
    Supply an optional ?thread_id=... query parameter to resume/share memory state.
    """
    logger.debug("Engine: executing workflow")
    try:
        final_state = run_workflow(request, thread_id=thread_id)

        return build_success_response("Workflow executed successfully", {
            "logs": final_state.get("logs", []),
            "final_state": {k: v for k, v in final_state.items() if k != "logs"},
            "thread_id": thread_id
        })
    except ValueError as e:
        raise_bad_request(str(e))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error executing workflow")
        raise_internal_server_error()



@router.post("/generate-code")
def generate_workflow_code(
    request: WorkflowPayload = Body(...),
    db: Session = Depends(get_db)
):
    """Convert a workflow JSON definition into executable LangGraph Python script."""
    logger.debug("Engine: generating Python source code")
    try:
        if request.skill_version_id:
            # Fetch from DB if ID is provided
            skill_graph = fetch_skill_graph(db, request.skill_version_id)
            workflow_data = {
                "nodes": [n.model_dump() for n in skill_graph.nodes],
                "connections": {k: v.model_dump() for k, v in skill_graph.connections.items()}
            }
        elif request.workflow_json:
            workflow_data = request.workflow_json
        elif request.nodes:
            # Fallback for direct node/edge input
            workflow_data = {"nodes": request.nodes, "connections": request.edges or {}}
        else:
            raise ValueError("Must provide either 'skill_version_id' or workflow definition.")

        source_code = generate_langgraph_source(workflow_data)
        return build_success_response("Python source generated successfully", {"code": source_code})
    except ValueError as e:
        raise_bad_request(str(e))
    except Exception:
        logger.exception("Error generating Python source")
        raise_internal_server_error()


@router.get("/generate-code/{skill_version_id}")
def generate_workflow_code_by_id(
    skill_version_id: str,
    db: Session = Depends(get_db)
):
    """Fetch a workflow from DB and convert it into executable LangGraph Python script."""
    logger.debug(f"Engine: generating Python source code for version {skill_version_id}")
    try:
        skill_graph = fetch_skill_graph(db, skill_version_id)
        workflow_data = {
            "nodes": [n.model_dump() for n in skill_graph.nodes],
            "connections": {k: v.model_dump() for k, v in skill_graph.connections.items()}
        }
        source_code = generate_langgraph_source(workflow_data)
        return build_success_response("Python source generated successfully", {"code": source_code})
    except Exception:
        logger.exception(f"Error generating Python source for {skill_version_id}")
        raise_internal_server_error()


# =========================================================================
# List available action handlers
# =========================================================================

@router.get("/actions")
def list_engine_actions():
    """Return a list of all built-in action_keys the engine supports."""
    logger.debug("Engine: listing registered actions")
    try:
        # Core built-in actions in node_executor.py
        actions = [
            {"action_key": "condition_check", "handler": "_handle_condition_check"},
            {"action_key": "save_result", "handler": "_handle_save_result"},
            {"action_key": "direct_reply", "handler": "_handle_direct_reply"},
            {"action_key": "*", "handler": "_handle_api_action (Dynamic)"},
        ]
        return build_success_response("Registered engine actions", {"items": actions, "total": len(actions)})
    except Exception:
        logger.exception("Error listing engine actions")
        raise_internal_server_error()
