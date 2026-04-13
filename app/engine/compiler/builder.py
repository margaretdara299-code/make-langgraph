"""
compiler/builder.py — Dynamically constructs a LangGraph StateGraph
from a validated workflow definition.

LangGraph design followed here:
  - One node = one function (wrapped via _make_node_fn closure)
  - Graph controls node-to-node movement via edges
  - Node functions do NOT call other node functions
  - entry point = the "start" node if present, else first node
  - Fail Fast: _make_node_fn checks state["error"] before invoking node
"""
from __future__ import annotations
import functools
import json
import hashlib
from langgraph.graph import StateGraph, END

from app.engine.models import WorkflowDef, WorkflowState
from app.engine.executor.node_executor import execute_node
from app.engine.compiler.validator import validate_workflow
from app.engine.compiler.sanitizer import build_unique_node_names


def compile_workflow_plan(workflow_json: dict) -> dict:
    """
    Validate a workflow JSON and produce a cacheable execution plan.
    Raises ValueError if the workflow fails structural validation.
    """
    result = validate_workflow(workflow_json)
    if not result["valid"]:
        raise ValueError("Workflow validation failed: " + "; ".join(result["errors"]))

    workflow_str = json.dumps(workflow_json, sort_keys=True)
    plan_hash    = hashlib.sha256(workflow_str.encode()).hexdigest()

    return {
        "compile_hash":  plan_hash,
        "valid":         True,
        "node_count":    result.get("node_count", 0),
        "edge_count":    result.get("edge_count", 0),
        "workflow_json": workflow_json,
    }


def build_graph(workflow_data: dict, checkpointer=None):
    """
    Build and return a compiled LangGraph from a workflow definition dict.
    Accepts either raw workflow JSON or a pre-compiled plan dict.
    """
    if "compile_hash" not in workflow_data:
        plan = compile_workflow_plan(workflow_data)
    else:
        plan = workflow_data

    wf_str      = json.dumps(plan["workflow_json"], sort_keys=True)
    state_graph = _build_stategraph(wf_str)
    return state_graph.compile(checkpointer=checkpointer)


# ─── Internal ──────────────────────────────────────────────────────────────────

def _make_node_fn(node_dict: dict):
    """
    Return a closure that executes a single node within the graph state.

    LangGraph rule: one node = one function.
    This closure does NOT call any other node function.

    Fail Fast: if state["error"] is already set by a previous node,
    the execute_node function will skip immediately (checked inside execute_node).
    """
    def _fn(state: WorkflowState) -> WorkflowState:
        if "logs" not in state or state["logs"] is None:
            state["logs"] = []
        if "node_responses" not in state or state["node_responses"] is None:
            state["node_responses"] = {}
        # Delegate to executor — which itself checks state["error"] first
        return execute_node(state, node_dict)
    return _fn


def _condition_router(state: WorkflowState) -> str:
    """Route conditional edges based on the 'condition_result' state key."""
    return state.get("condition_result", "false")


@functools.lru_cache(maxsize=128)
def _build_stategraph(workflow_str: str) -> StateGraph:
    """
    Build the uncompiled StateGraph from a JSON string.
    Cached by workflow_str to avoid redundant rebuilds for identical graphs.

    Entry point selection:
      - If a node with type="start" exists → set_entry_point to that node
        and wire an edge: start → first_action_node
      - Otherwise → set_entry_point to first node in the list
    """
    wf    = WorkflowDef(**json.loads(workflow_str))
    graph = StateGraph(WorkflowState)

    id_map = build_unique_node_names(
        [(n.id, n.data.actionKey or n.data.label or n.id) for n in wf.nodes]
    )

    # Register ALL nodes (including start)
    for node in wf.nodes:
        graph.add_node(id_map[node.id], _make_node_fn(node.model_dump()))

    # ── Entry point: prefer "start" type node, else first node ─────────
    start_node = next((n for n in wf.nodes if n.type == "start"), None)
    if start_node:
        graph.set_entry_point(id_map[start_node.id])
    else:
        graph.set_entry_point(id_map[wf.nodes[0].id])

    # ── Wire edges from connections ────────────────────────────────────
    conditional_sources: dict[str, dict[str, str]] = {}
    normal_edges: list[tuple[str, str]] = []

    for edge in wf.connections.values():
        src = id_map.get(edge.source)
        tgt = id_map.get(edge.target)
        if not src or not tgt:
            continue

        cond_value = (edge.condition or {}).get("value")
        if cond_value in ("true", "false") and not edge.is_default:
            conditional_sources.setdefault(src, {})[cond_value] = tgt
        else:
            normal_edges.append((src, tgt))

    for src, tgt in normal_edges:
        if src not in conditional_sources:
            graph.add_edge(src, tgt)

    for src, branch_map in conditional_sources.items():
        graph.add_conditional_edges(src, _condition_router, branch_map)

    # ── Terminate leaf nodes (nodes with no outgoing edges) ────────────
    sources_set = {id_map.get(e.source) for e in wf.connections.values() if id_map.get(e.source)}
    for node in wf.nodes:
        lg_id = id_map.get(node.id)
        if lg_id and lg_id not in sources_set:
            graph.add_edge(lg_id, END)

    return graph
