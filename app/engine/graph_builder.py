"""
Graph Builder — dynamically constructs a LangGraph StateGraph from a workflow JSON definition.
Supports normal edges, conditional branching via condition nodes, and caching.
"""
from __future__ import annotations
import functools
import json
import hashlib
from langgraph.graph import StateGraph, END

from app.engine.models import WorkflowDef, WorkflowState
from app.engine.node_executor import execute_node
from app.engine.validator import validate_workflow


def compile_workflow_plan(workflow_json: dict) -> dict:
    """
    Validate and compile a workflow JSON into a cacheable execution plan.
    """
    val_result = validate_workflow(workflow_json)
    if not val_result["valid"]:
        raise ValueError("Workflow validation failed: " + "; ".join(val_result["errors"]))
    
    workflow_str = json.dumps(workflow_json, sort_keys=True)
    plan_hash = hashlib.sha256(workflow_str.encode("utf-8")).hexdigest()
    
    return {
        "compile_hash": plan_hash,
        "valid": True,
        "node_count": val_result.get("node_count", 0),
        "edge_count": val_result.get("edge_count", 0),
        "workflow_json": workflow_json
    }


def _make_node_fn(node_dict: dict):
    """Closure for each LangGraph node."""
    def _node_fn(state: WorkflowState) -> WorkflowState:
        if "logs" not in state or state["logs"] is None:
            state["logs"] = []
        return execute_node(state, node_dict)
    return _node_fn


def _condition_router(state: WorkflowState) -> str:
    """Read condition_result from state to resolve branching."""
    return state.get("condition_result", "false")


@functools.lru_cache(maxsize=128)
def _build_stategraph(workflow_str: str) -> StateGraph:
    """
    Builds the uncompiled StateGraph.
    Cached based on the stringified workflow to avoid rebuilding identical graphs.
    """
    workflow_json = json.loads(workflow_str)
    wf = WorkflowDef(**workflow_json)

    graph = StateGraph(WorkflowState)

    # 1. Add nodes
    for node in wf.nodes:
        graph.add_node(node.id, _make_node_fn(node.model_dump()))

    # 2. Entry point
    entry_node_id = wf.nodes[0].id
    graph.set_entry_point(entry_node_id)

    # 3. Wire edges
    conditional_sources: dict[str, dict[str, str]] = {}
    normal_edges: list[tuple[str, str]] = []

    for edge in wf.connections.values():
        # Edge condition is a dict in the DB format, e.g. {"value": "true"} or {"expr": "..."}
        cond_data = edge.condition or {}
        cond_value = cond_data.get("value")
        
        if cond_value in ("true", "false") and not edge.is_default:
            conditional_sources.setdefault(edge.source, {})[cond_value] = edge.target
        else:
            normal_edges.append((edge.source, edge.target))

    for src, tgt in normal_edges:
        if src not in conditional_sources:
            graph.add_edge(src, tgt)

    for src, branch_map in conditional_sources.items():
        graph.add_conditional_edges(src, _condition_router, branch_map)

    # 4. Terminal nodes
    sources_set = {e.source for e in wf.connections.values()}
    for node in wf.nodes:
        if node.id not in sources_set:
            graph.add_edge(node.id, END)

    return graph


def build_graph(workflow_data: dict, checkpointer=None):
    """
    Parse a workflow JSON dict (or compiled plan) and return a compiled LangGraph.
    """
    # If raw JSON is passed, compile it first to validate
    if "compile_hash" not in workflow_data:
        plan = compile_workflow_plan(workflow_data)
    else:
        plan = workflow_data
        
    wf_str = json.dumps(plan["workflow_json"], sort_keys=True)
    
    # Fetch from cache or build
    state_graph = _build_stategraph(wf_str)
    
    # Return compiled engine (with optional checkpointer for memory)
    return state_graph.compile(checkpointer=checkpointer)
