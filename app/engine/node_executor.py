"""
Node Executor — runs every action inside a workflow node sequentially.
"""
from __future__ import annotations

def _handle_condition_check(state: dict, config: dict) -> dict:
    """Migrated from action_registry.py."""
    field = config.get("field", "last_result")
    op = config.get("op", "exists")
    value = config.get("value")
    actual = state.get(field)

    result = False
    if op == "exists":
        result = actual is not None
    elif op == "eq":
        result = actual == value
    elif op == "gt":
        result = actual is not None and actual > value
    elif op == "lt":
        result = actual is not None and actual < value

    state["condition_result"] = "true" if result else "false"
    state["logs"].append(f"    [MODAL:COND] {field} {op} {value}  →  {state['condition_result']}")
    return state


def _handle_save_result(state: dict, config: dict) -> dict:
    """Migrated from action_registry.py."""
    state["saved_data"] = state.get("last_result")
    state["logs"].append(f"    [MODAL:SAVE] Last result saved locally")
    return state


def _handle_direct_reply(state: dict, config: dict) -> dict:
    """Migrated from action_registry.py."""
    message = config.get("message", "Workflow step complete.")
    state["final_reply"] = message
    state["logs"].append(f"    [MODAL:REPLY] {message}")
    return state


def _handle_api_action(state: dict, action_key: str, config: dict) -> dict:
    """Generic handler for any action not handled internally (dynamic API calls)."""
    # In a real system, this would make an external HTTP request
    state["logs"].append(f"    [MODAL:API] Calling external action: {action_key}")
    
    # Simulate a generic response
    state["last_result"] = {"action": action_key, "status": "simulated_success", "payload": config}
    return state


def execute_node(state: dict, node: dict) -> dict:
    """
    Execute all actions within a single workflow node.
    Refactored to handle core logic internally and delegate to API calls.
    """
    node_id = node["id"]
    node_type = node.get("type", "action")
    data = node.get("data", {})
    node_name = data.get("label") or node_id
    
    state["logs"].append(f"▶ Node [{node_id}] \"{node_name}\" ({node_type}) — start")

    action_key = data.get("actionKey") or data.get("action_key")
    config = data.get("config") or data.get("configurationsJson") or {}
    
    if action_key:
        if action_key == "condition_check":
            state = _handle_condition_check(state, config)
        elif action_key == "save_result":
            state = _handle_save_result(state, config)
        elif action_key == "direct_reply":
            state = _handle_direct_reply(state, config)
        else:
            # All other actions are treated as dynamic API calls
            state = _handle_api_action(state, action_key, config)

    elif node_type.startswith("trigger."):
        state["logs"].append("    [TRIGGER] Workflow entered")
    elif node_type.startswith("end."):
        state["logs"].append(f"    [END] Reach terminal node: {node_type}")
    else:
        state["logs"].append(f"    (Pass-through node)")

    state["logs"].append(f"◀ Node [{node_id}] — done\n")
    return state
