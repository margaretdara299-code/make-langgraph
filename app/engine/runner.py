"""
Runner — orchestrate workflow execution and print debug output.

Usage (standalone):
    python -m app.engine.runner
"""
from __future__ import annotations

import json
import os

from langgraph.checkpoint.memory import MemorySaver
from app.engine.graph_builder import build_graph
from app.engine.models import WorkflowState


def run_workflow(workflow_data: dict, thread_id: str = "default_session") -> WorkflowState:
    """
    Build a LangGraph from the workflow JSON, invoke it, and return the final state.
    Supports checkpointing (memory/resume) based on thread_id.
    """

    # ✅ Use in-memory checkpoint (stable)
    memory = MemorySaver()

    # Build compiled graph
    compiled = build_graph(workflow_data, checkpointer=memory)

    # Initial empty state
    initial_state: WorkflowState = {
        "logs": [],
        "last_result": None,
        "http_response": None,
        "saved_data": None,
        "final_reply": "",
        "condition_result": "",
    }

    # Thread config (for session-based execution)
    config = {"configurable": {"thread_id": thread_id}}

    # Execute workflow
    final_state = compiled.invoke(initial_state, config=config)

    return final_state


def _print_results(state: WorkflowState) -> None:
    """Pretty-print execution logs and final state."""
    print("\n" + "=" * 60)
    print("  WORKFLOW EXECUTION LOGS")
    print("=" * 60)

    for line in state.get("logs", []):
        print(line)

    print("=" * 60)
    print("  FINAL STATE")
    print("=" * 60)

    display = {k: v for k, v in state.items() if k != "logs"}
    print(json.dumps(display, indent=2, default=str))

    print("=" * 60 + "\n")


# ── CLI entry point ───────────────────────────────────────────────────
if __name__ == "__main__":
    sample_path = os.path.join(os.path.dirname(__file__), "sample_workflow.json")

    with open(sample_path, "r", encoding="utf-8") as f:
        workflow = json.load(f)

    print("Loading valid sample workflow …")

    state = run_workflow(workflow, thread_id="test_run_1")

    _print_results(state)