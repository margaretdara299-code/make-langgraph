"""
executor/node_executor.py — Executes individual workflow nodes.

Handles built-in node types (condition_check, save_result, direct_reply)
and delegates all other action nodes to the generic HTTPX API caller.
"""
from __future__ import annotations
import httpx


# ─── Built-in Node Handlers ────────────────────────────────────────────────────

def _handle_condition_check(state: dict, config: dict) -> dict:
    """Evaluate a field condition and write 'true'/'false' to condition_result."""
    field  = config.get("field", "last_result")
    op     = config.get("op", "exists")
    value  = config.get("value")
    actual = state.get(field)

    result = False
    if   op == "exists": result = actual is not None
    elif op == "eq":     result = actual == value
    elif op == "gt":     result = actual is not None and actual > value
    elif op == "lt":     result = actual is not None and actual < value

    state["condition_result"] = "true" if result else "false"
    state["logs"].append(f"    [COND] {field} {op} {value}  →  {state['condition_result']}")
    return state


def _handle_save_result(state: dict, config: dict) -> dict:
    """Save last_result into saved_data for later use."""
    state["saved_data"] = state.get("last_result")
    state["logs"].append("    [SAVE] last_result → saved_data")
    return state


def _handle_direct_reply(state: dict, config: dict) -> dict:
    """Set a static final_reply message on the state."""
    message = config.get("message", "Workflow step complete.")
    state["final_reply"] = message
    state["logs"].append(f"    [REPLY] {message}")
    return state


# ─── Generic HTTP API Handler ──────────────────────────────────────────────────

def _handle_http_action(state: dict, action_key: str, config: dict, node_id: str) -> dict:
    """
    Execute any external API action using httpx.

    Reads from config:
        url           — endpoint to call (required)
        method        — HTTP method (default: GET)
        output_key    — state key to write the response to (default: last_result)
        path_params   — list[{key, value}] substituted into the URL path
        query_params  — list[{key, value}] appended as query string
        header_params — list[{key, value}] sent as HTTP headers
        body_params   — list[{key, value}] or dict sent as JSON body
    """
    url        = config.get("url")
    method     = config.get("method", "GET").upper()
    output_key = config.get("output_key", "last_result")

    if not url:
        state["logs"].append(f"    [API] ✗ No URL configured for '{action_key}'")
        state[output_key] = {"error": "No URL configured"}
        return state

    state["logs"].append(f"    [API] {method} {url}")

    # Resolve path params  (:key → value)
    for p in config.get("path_params") or []:
        if p and "key" in p and "value" in p:
            url = url.replace(f":{p['key']}", str(p["value"]))

    # Query string
    params = {
        q["key"]: q["value"]
        for q in (config.get("query_params") or [])
        if q and "key" in q and "value" in q
    }

    # Headers
    headers = {
        h["key"]: h["value"]
        for h in (config.get("header_params") or [])
        if h and "key" in h and "value" in h
    }

    # JSON body
    body_raw  = config.get("body_params")
    json_body = None
    if isinstance(body_raw, list):
        json_body = {b["key"]: b["value"] for b in body_raw if b and "key" in b and "value" in b}
    elif isinstance(body_raw, dict):
        json_body = body_raw

    try:
        with httpx.Client() as client:
            response = client.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                json=json_body if method in ("POST", "PUT", "PATCH") else None,
                timeout=10.0,
            )
            response.raise_for_status()

            result = response.json() if response.text else {}
            state["logs"].append(f"    [API] ✓ {response.status_code}")
            state[output_key]      = result
            state["last_result"]   = result
            state["node_responses"][node_id] = result
            state["http_response"] = {"status_code": response.status_code, "url": str(response.url)}

    except httpx.HTTPStatusError as exc:
        state["logs"].append(f"    [API] ✗ HTTP {exc.response.status_code}")
        err_out = {"error": f"HTTP {exc.response.status_code}", "detail": exc.response.text}
        state[output_key] = err_out
        state["node_responses"][node_id] = err_out

    except Exception as exc:
        state["logs"].append(f"    [API] ✗ {exc}")
        err_out = {"error": "Request failed", "detail": str(exc)}
        state[output_key] = err_out
        state["node_responses"][node_id] = err_out

    return state


# ─── Public Entry Point ────────────────────────────────────────────────────────

def execute_node(state: dict, node: dict) -> dict:
    """
    Execute a single workflow node.
    Dispatches to built-in handlers or the generic HTTP action executor.
    """
    node_id   = node["id"]
    node_type = node.get("type", "action")
    data      = node.get("data", {})
    label     = data.get("label") or node_id

    state["logs"].append(f"▶ [{label}] ({node_type})")

    action_key = data.get("actionKey") or data.get("action_key")
    config     = (
        data.get("config")
        or data.get("configurationsJson")
        or data.get("configurations_json")
        or {}
    )

    if action_key:
        if   action_key == "condition_check": state = _handle_condition_check(state, config)
        elif action_key == "save_result":     state = _handle_save_result(state, config)
        elif action_key == "direct_reply":    state = _handle_direct_reply(state, config)
        else:                                  state = _handle_http_action(state, action_key, config, node_id)
    elif node_type.startswith("trigger."):
        state["logs"].append("    [TRIGGER] Workflow entered")
    elif node_type.startswith("end."):
        state["logs"].append(f"    [END] {node_type}")
    else:
        state["logs"].append("    [PASS] No action configured")

    state["logs"].append(f"◀ [{label}] done\n")
    return state
