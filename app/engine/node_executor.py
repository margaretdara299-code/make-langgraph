"""
Node Executor — runs every action inside a workflow node sequentially.
"""
from __future__ import annotations
from app.engine.action_registry import ACTION_REGISTRY


def execute_node(state: dict, node: dict) -> dict:
    """
    Execute all actions within a single workflow node.

    Args:
        state: The mutable workflow state dict.
        node:  A dict with keys  id, name, actions[].

    Returns:
        The updated state after all actions have run.
    """
    node_id = node["id"]
    node_type = node.get("type", "action")
    data = node.get("data", {})
    node_name = data.get("label") or node_id
    
    state["logs"].append(f"▶ Node [{node_id}] \"{node_name}\" ({node_type}) — start")

    # In the React Flow / Skill Designer format, action details are directly in node.data
    action_key = data.get("actionKey") or data.get("action_key")
    
    if action_key:
        config = data.get("config") or data.get("configurationsJson") or {}
        capability = data.get("capability", "unknown")

        handler = ACTION_REGISTRY.get(action_key)
        if handler is None:
            state["logs"].append(f"    ⚠ No handler for action_key='{action_key}' — skipped")
        else:
            state["logs"].append(f"  ● Action: {action_key} (capability: {capability})")
            state = handler(state, config)
    elif node_type.startswith("trigger."):
        state["logs"].append("    [TRIGGER] Workflow entered")
    elif node_type.startswith("end."):
        state["logs"].append(f"    [END] Reach terminal node: {node_type}")
    else:
        state["logs"].append(f"    (Pass-through node)")

    state["logs"].append(f"◀ Node [{node_id}] — done\n")
    return state
