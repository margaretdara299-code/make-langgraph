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
