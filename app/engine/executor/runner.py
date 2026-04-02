"""
executor/runner.py — Orchestrates end-to-end workflow execution.

Public API:
    run_workflow(workflow_data, thread_id) -> WorkflowState
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from app.engine.compiler.builder import build_graph
from app.engine.models import WorkflowState


def run_workflow(workflow_data: dict, thread_id: str = "default_session") -> WorkflowState:
    """
    Compile and execute a LangGraph workflow from a workflow definition dict.

    Args:
        workflow_data:  Dict containing 'nodes' and 'connections'.
        thread_id:      Session identifier for checkpointing (enables resume capability).

    Returns:
        The final WorkflowState after all nodes have executed.
    """
    compiled     = build_graph(workflow_data, checkpointer=MemorySaver())
    config       = {"configurable": {"thread_id": thread_id}}
    initial: WorkflowState = {
        "logs":             [],
        "last_result":      None,
        "http_response":    None,
        "saved_data":       None,
        "final_reply":      "",
        "condition_result": "",
        "node_responses":   {},
    }
    return compiled.invoke(initial, config=config)
