"""
Python Code Generation Service — converts workflow JSON into executable LangGraph source code.
"""
from __future__ import annotations
from app.engine.models import WorkflowDef
from app.engine.sanitizer import build_unique_node_names


_HEADER = '''\
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END


class WorkflowState(TypedDict, total=False):
    """Shared state context."""
    last_result: any
    http_response: any
    saved_data: any
    final_reply: str
    condition_result: str
    logs: list[str]

'''

_NODE_FUNCTION_TEMPLATE = '''\
def {fn_name}(state: WorkflowState) -> WorkflowState:
    """Execution logic for node '{lg_name}'."""
    print(f"--- Executing: {lg_name} ---")
    # TODO: Implement custom logic for {action_key}
    return state

'''

_BUILDER_HEADER = '''\
# --- Graph Construction ---
builder = StateGraph(WorkflowState)
'''

_ADD_NODE_TEMPLATE = 'builder.add_node("{lg_name}", {fn_name})\n'
_ADD_EDGE_TEMPLATE = 'builder.add_edge("{source}", "{target}")\n'
_ADD_START_EDGE = 'builder.set_entry_point("{root}")\n'
_ADD_END_EDGE = 'builder.add_edge("{leaf}", END)\n'
_FOOTER = "\ngraph = builder.compile()\n"


def generate_langgraph_source(workflow_data: dict) -> str:
    """
    Generate a complete, executable Python script from the workflow definition.
    """
    wf = WorkflowDef(**workflow_data)
    
    # 1. Build unique, sanitized node names
    name_inputs = [(n.id, n.data.actionKey or n.data.label or n.id) for n in wf.nodes]
    id_map = build_unique_node_names(name_inputs)
    
    lines: list[str] = [_HEADER]

    # 2. Add placeholder functions for each node
    for node in wf.nodes:
        lg_id = id_map[node.id]
        lines.append(
            _NODE_FUNCTION_TEMPLATE.format(
                fn_name=f"exec_{lg_id}",
                lg_name=lg_id,
                action_key=node.data.actionKey or "custom_logic"
            )
        )

    lines.append(_BUILDER_HEADER)

    # 3. Register nodes
    for node in wf.nodes:
        lg_id = id_map[node.id]
        lines.append(
            _ADD_NODE_TEMPLATE.format(
                lg_name=lg_id,
                fn_name=f"exec_{lg_id}"
            )
        )

    lines.append("")
    
    # 4. Set entry point
    if wf.nodes:
        root_node = id_map[wf.nodes[0].id]
        lines.append(_ADD_START_EDGE.format(root=root_node))

    # 5. Add edges
    conditional_sources: set[str] = set()
    for edge in wf.connections.values():
        lg_source = id_map[edge.source]
        lg_target = id_map[edge.target]
        
        # Check if it's a conditional edge (based on current engine logic)
        cond_data = edge.condition or {}
        cond_value = cond_data.get("value")
        
        if cond_value in ("true", "false") and not edge.is_default:
            # For brevity in codegen, we note the branching. 
            # In a real generator, we'd add conditional_edges logic here.
            lines.append(f'# Conditional: from {lg_source} to {lg_target} if result is {cond_value}\n')
            conditional_sources.add(lg_source)
        
        lines.append(
            _ADD_EDGE_TEMPLATE.format(
                source=lg_source,
                target=lg_target
            )
        )

    # 6. Terminal edges to END
    sources_set = {id_map[e.source] for e in wf.connections.values()}
    for node in wf.nodes:
        lg_id = id_map[node.id]
        if lg_id not in sources_set:
            lines.append(_ADD_END_EDGE.format(leaf=lg_id))

    lines.append(_FOOTER)

    return "".join(lines)
