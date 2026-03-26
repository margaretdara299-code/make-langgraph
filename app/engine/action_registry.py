"""
Action Registry — global handler mapping and all capability handlers.

Every handler has the signature:
    handler(state: dict, config: dict) -> dict

Handlers SIMULATE real work (no actual DB / HTTP calls).
"""
from __future__ import annotations
from typing import Any, Callable


# =========================================================================
# Handlers
# =========================================================================

def database_handler(state: dict, config: dict) -> dict:
    """Simulate a database query. Stores result in state['last_result']."""
    query = config.get("query", "SELECT 1")
    simulated_rows = [
        {"id": 1, "value": "row_a"},
        {"id": 2, "value": "row_b"},
    ]
    state["last_result"] = {"query": query, "rows": simulated_rows}
    state["logs"].append(f"    [DB] Executed query: {query}  →  {len(simulated_rows)} rows")
    return state


def http_handler(state: dict, config: dict) -> dict:
    """Simulate an HTTP request. Stores response in state['http_response']."""
    url = config.get("url", "https://example.com/api")
    method = config.get("method", "GET").upper()
    simulated_response = {"status": 200, "body": {"message": "OK"}}
    state["http_response"] = simulated_response
    state["logs"].append(f"    [HTTP] {method} {url}  →  {simulated_response['status']}")
    return state


def save_handler(state: dict, config: dict) -> dict:
    """Custom function — copies last_result into state['saved_data']."""
    state["saved_data"] = state.get("last_result")
    state["logs"].append(f"    [SAVE] Saved last_result → saved_data")
    return state


def condition_handler(state: dict, config: dict) -> dict:
    """
    Evaluate a condition against the current state.
    Sets state['condition_result'] to "true" or "false".

    Config keys:
        field   — state key to inspect
        op      — operator: "exists", "eq", "gt", "lt"
        value   — comparison value (for eq/gt/lt)
    """
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
    state["logs"].append(f"    [COND] {field} {op} {value}  →  {state['condition_result']}")
    return state


def reply_handler(state: dict, config: dict) -> dict:
    """Produce the final reply / output message."""
    template = config.get("message", "Workflow complete.")
    state["final_reply"] = template
    state["logs"].append(f"    [REPLY] {template}")
    return state


# =========================================================================
# Global Registry
# =========================================================================

ACTION_REGISTRY: dict[str, Callable[[dict, dict], dict]] = {
    "database_query":   database_handler,
    "http_request":     http_handler,
    "save_result":      save_handler,
    "condition_check":  condition_handler,
    "direct_reply":     reply_handler,
}
