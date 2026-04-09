"""
executor/runner.py — Orchestrates end-to-end workflow execution.

Public API:
    run_workflow(workflow_data, thread_id) -> WorkflowState
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from app.engine.compiler.builder import build_graph
from app.engine.models import WorkflowState


def _extract_start_node_state(workflow_data: dict) -> dict:
    """
    Find the Start node in the graph and extract its initial_state key-value
    pairs into a plain dict. These act as workflow-level default variables.

    initial_state format (from UI): [{"key": "case_id", "value": ""}]
    """
    defaults: dict = {}
    nodes = workflow_data.get("nodes") or []
    for node in nodes:
        if node.get("type") == "start":
            initial_state = node.get("data", {}).get("initial_state") or []
            for item in initial_state:
                if isinstance(item, dict) and item.get("key"):
                    # Only set default if value is non-empty; runtime payload overrides
                    defaults[item["key"]] = item.get("value", "")
    return defaults


def run_workflow(workflow_data: dict, initial_input: dict | None = None, thread_id: str = "default_session") -> WorkflowState:
    """
    Compile and execute a LangGraph workflow from a workflow definition dict.

    Args:
        workflow_data:  Dict containing 'nodes' and 'connections'.
        initial_input:  Optional dict with runtime data (e.g. {"case_id": "2"}).
                        Runtime payload overrides Start node defaults for the same key.
        thread_id:      Session identifier for checkpointing.

    Returns:
        The final WorkflowState after all nodes have executed.
    """
    # 1. Extract defaults defined in the Start node's "Initial State Variables"
    start_defaults = _extract_start_node_state(workflow_data)

    # 2. Merge: start node defaults < runtime payload (runtime wins for same key)
    merged_saved_data = {**start_defaults, **(initial_input or {})}

    compiled     = build_graph(workflow_data, checkpointer=MemorySaver())
    config       = {"configurable": {"thread_id": thread_id}}
    initial: WorkflowState = {
        "logs":             [],
        "last_result":      None,
        "http_response":    None,
        "saved_data":       merged_saved_data,
        "final_reply":      "",
        "condition_result": "",
        "node_responses":   {},
        "error":            None,   # None = OK | "msg" = FAIL FAST
    }
    return compiled.invoke(initial, config=config)

