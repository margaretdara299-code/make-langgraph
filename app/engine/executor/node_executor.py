"""
executor/node_executor.py — Executes individual workflow nodes.

LangGraph rules enforced here:
  - Each node function does ONLY its own work, then returns state.
  - No node calls another node function directly.
  - On error: write state["error"] = message, return state immediately.
  - Caller (builder.py) checks state["error"] before invoking next node.
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
    msg = config.get("message", "Workflow step complete.")
    state["final_reply"] = msg
    state["logs"].append(f"    [REPLY] {msg}")
    return state


# ─── Shared Value Resolver ───────────────────────────────────────────────────

def _resolve_param(val, key: str, ctx: dict):
    """
    Resolve a single config value against runtime context.

    Rules:
      - None / "" / "null" / "undefined"  → ctx[key] or Python None
      - {{var}} template                  → ctx[var]  or Python None
      - "true" / "false"                  → Python bool
      - Anything else (incl. "0")         → return as-is
    """
    if val is None or (isinstance(val, str) and val.strip().lower() in ("", "null", "undefined")):
        return ctx.get(key, None)
    if isinstance(val, str) and val.startswith("{{") and val.endswith("}}"):
        return ctx.get(val[2:-2].strip(), None)
    if isinstance(val, str):
        if val.strip().lower() == "true":  return True
        if val.strip().lower() == "false": return False
    return val


# ── Generic HTTP API Handler ──────────────────────────────────────────────

def _handle_http_action(state: dict, action_key: str, config: dict, node_id: str) -> dict:
    """
    Execute one external API call for this node.

    Rules:
      - Only this node’s HTTP call is made here.
      - On any failure, write state["error"] and return immediately.
      - Do NOT call any other node function from here.
    """
    url        = config.get("url")
    method     = config.get("method", "GET").upper()
    output_key = config.get("output_key", "last_result")

    if not url:
        error_msg = f"No URL configured for action '{action_key}'"
        state["logs"].append(f"    [API] ✗ {error_msg}")
        state["error"] = error_msg
        state["node_responses"][node_id] = {"error": error_msg}
        return state

    # Build context: saved_data + last_result.data
    ctx: dict = {}
    if isinstance(state.get("saved_data"), dict):
        ctx.update(state["saved_data"])
    if isinstance(state.get("last_result"), dict):
        last  = state["last_result"]
        inner = last.get("data") if isinstance(last, dict) else None
        ctx.update(inner if isinstance(inner, dict) else last)

    state["logs"].append(f"    [API] {method} {url}")

    # Resolve :path_params
    for p in config.get("path_params") or []:
        if not p or "key" not in p:
            continue
        val = _resolve_param(p.get("value"), p["key"], ctx)
        url = url.replace(f":{p['key']}", str(val) if val is not None else "")

    # Query string
    params: dict = {}
    for q in (config.get("query_params") or []):
        if not q or "key" not in q:
            continue
        params[q["key"]] = _resolve_param(q.get("value"), q["key"], ctx)

    # Headers
    headers: dict = {
        h["key"]: h["value"]
        for h in (config.get("header_params") or [])
        if h and "key" in h and "value" in h
    }

    # JSON body
    body_raw  = config.get("body_params")
    json_body: dict = {}

    if isinstance(body_raw, list):
        for b in body_raw:
            if not b or "key" not in b:
                continue
            json_body[b["key"]] = _resolve_param(b.get("value"), b["key"], ctx)
    elif isinstance(body_raw, dict):
        for bk, bv in body_raw.items():
            json_body[bk] = _resolve_param(bv, bk, ctx)

    # Inject ALL extra ctx keys not explicitly declared in body_params
    # (ensures case_id, claim_id etc. from saved_data always flow through)
    for ck, cv in ctx.items():
        if ck not in json_body:
            json_body[ck] = cv


    # ── Execute HTTP Request ──────────────────────────────────────────
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
            state[output_key]             = result
            state["last_result"]          = result
            state["node_responses"][node_id] = result
            state["http_response"]        = {
                "status_code": response.status_code,
                "url":         str(response.url),
            }
            state["error"] = None   # clear any previous transient error

    except httpx.HTTPStatusError as exc:
        error_msg = f"HTTP {exc.response.status_code} from {url}"
        state["logs"].append(f"    [API] ✗ {error_msg}")
        err_payload = {"error": error_msg, "detail": exc.response.text}
        state[output_key]                = err_payload
        state["node_responses"][node_id] = err_payload
        state["error"]                   = error_msg   # ← FAIL FAST signal

    except Exception as exc:
        error_msg = f"Request failed: {exc}"
        state["logs"].append(f"    [API] ✗ {error_msg}")
        err_payload = {"error": error_msg}
        state[output_key]                = err_payload
        state["node_responses"][node_id] = err_payload
        state["error"]                   = error_msg   # ← FAIL FAST signal

    return state


# ─── Public Entry Point ────────────────────────────────────────────────────────

def execute_node(state: dict, node: dict) -> dict:
    """
    Execute a single workflow node.

    Rules:
      - Checks state["error"] first; if set, skips and returns immediately (FAIL FAST).
      - Otherwise dispatches to the correct built-in or HTTP handler.
      - Each handler does ONLY its own work and returns state.
      - No handler calls another handler or node directly.
    """
    node_id   = node["id"]
    node_type = node.get("type", "action")
    data      = node.get("data", {})
    label     = data.get("label") or node_id

    # ── FAIL FAST: skip if a previous node already set an error ──────
    if state.get("error"):
        state["logs"].append(f"⏭ [{label}] SKIPPED — previous error: {state['error']}")
        return state

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
        else:                                 state = _handle_http_action(state, action_key, config, node_id)
    elif node_type == "start":
        # start node = pass-through entry point, just log and continue
        state["logs"].append("    [START] Workflow entered")
    elif node_type.startswith("trigger."):
        state["logs"].append("    [TRIGGER] Workflow entered")
    elif node_type.startswith("end."):
        state["logs"].append(f"    [END] {node_type}")
    else:
        state["logs"].append("    [PASS] No action configured")

    state["logs"].append(f"◀ [{label}] done\n")
    return state
