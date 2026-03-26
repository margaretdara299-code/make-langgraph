"""
Engine controller — API routes for the Workflow Execution Engine.
"""
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Any
from app.common.response import build_success_response, raise_internal_server_error, raise_bad_request
from app.engine.runner import run_workflow
from app.engine.validator import validate_workflow
from app.engine.graph_builder import compile_workflow_plan
from app.engine.action_registry import ACTION_REGISTRY
from app.logger.logging import logger

router = APIRouter(prefix="/api", tags=["Workflow Engine"])


# ── Request models ─────────────────────────────────────────────────────
class WorkflowPayload(BaseModel):
    """Payload containing a workflow JSON definition, or a compiled plan."""
    nodes: list[dict[str, Any]] | None = None
    edges: list[dict[str, Any]] | None = None
    compile_hash: str | None = None
    workflow_json: dict[str, Any] | None = None


# =========================================================================
# Validate a workflow
# =========================================================================

@router.post("/engine/validate")
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

@router.post("/engine/compile")
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

@router.post("/engine/run", status_code=200)
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


# =========================================================================
# List available action handlers
# =========================================================================

@router.get("/engine/actions")
def list_engine_actions():
    """Return a list of all registered action_keys the engine supports."""
    logger.debug("Engine: listing registered actions")
    try:
        actions = [
            {"action_key": key, "handler": fn.__name__}
            for key, fn in ACTION_REGISTRY.items()
        ]
        return build_success_response("Registered engine actions", {"items": actions, "total": len(actions)})
    except Exception:
        logger.exception("Error listing engine actions")
        raise_internal_server_error()
