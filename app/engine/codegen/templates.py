"""
Code Generation Templates — all Python source templates used for generating
standalone LangGraph projects from a workflow definition.

Design:
  - action_configs.py  → full DB configuration per action (url, method, all params)
  - helpers.py         → run_api_node(state, action_key) — the ONLY shared caller
  - langgraph_workflow.py → each node calls run_api_node(state, "action_key") only
  - Fail Fast          → state["error"] set on failure, all next nodes skip
"""

# ─── action_configs.py Template ───────────────────────────────────────────────
# Header and footer are static; ACTION_CONFIGS entries are injected by generator.py
ACTION_CONFIGS_PY_HEADER = '''\
"""
action_configs.py — Full API configuration for every workflow action node.

Mirrors exactly what is stored in the database:
  url          : full endpoint URL (supports :path_param syntax)
  method       : HTTP method (GET, POST, PUT, PATCH, DELETE)
  path_params  : list of {key, value} — resolved into the URL path
  query_params : list of {key, value} — appended as ?key=value
  header_params: list of {key, value} — sent as HTTP headers
  body_params  : dict {field: default_value} — sent as JSON body

Runtime values (e.g. case_id, claim_id) are auto-resolved from state context.
Edit only this file to change URLs, methods, or params — never touch node functions.
"""

ACTION_CONFIGS = {
'''

ACTION_CONFIGS_PY_ENTRY = '''\
    "{action_key}": {{
        "url":           "{url}",
        "method":        "{method}",
        "path_params":   {path_params_repr},
        "query_params":  {query_params_repr},
        "header_params": {header_params_repr},
        "body_params":   {body_params_repr},
    }},
'''

ACTION_CONFIGS_PY_FOOTER = '''\
}
'''


# ─── helpers.py Template ──────────────────────────────────────────────────────
HELPERS_PY = '''\
"""
helpers.py — Single shared HTTP API caller for all workflow nodes.

Usage in every node:
    return run_api_node(state, "action_key")

How it works:
  1. Looks up full config from ACTION_CONFIGS["action_key"]
  2. Builds context from state["saved_data"] + state["last_result"]["data"]
  3. Resolves :path_params, query_params, body_params from context
  4. Calls the API and writes result to state["last_result"]
  5. On any error: sets state["error"] = message (FAIL FAST — next nodes skip)
"""
from __future__ import annotations
import httpx
from action_configs import ACTION_CONFIGS


def _build_context(state: dict) -> dict:
    """
    Build a flat context dict from:
      - state["saved_data"]         : initial payload injected at run start
      - state["last_result"]["data"]: output from the previous node (unwrap envelope)

    last_result takes priority over saved_data for the same key.
    """
    ctx: dict = {}
    if isinstance(state.get("saved_data"), dict):
        ctx.update(state["saved_data"])
    if isinstance(state.get("last_result"), dict):
        last  = state["last_result"]
        inner = last.get("data") if "data" in last else last
        if isinstance(inner, dict):
            ctx.update(inner)
    return ctx


def _resolve_value(val, key: str, ctx: dict):
    """
    Resolve a config value against the runtime context.
    If val is empty, "null", or "undefined" → look up key in ctx. If not in ctx, return Python None.
    If val is a {{template}} → replace with ctx[variable].
    Evaluates literal "true" / "false" to booleans.
    Otherwise return val as-is.
    """
    str_val = str(val).strip().lower()

    if val is None or str_val in ("", "null", "undefined"):
        return ctx.get(key, None)
    
    if isinstance(val, str) and val.startswith("{{") and val.endswith("}}"):
        var = val[2:-2].strip()
        return ctx.get(var, None)

    if str_val == "true": return True
    if str_val == "false": return False

    return val


def run_api_node(state: dict, action_key: str) -> dict:
    """
    Execute one HTTP API call for a workflow node.

    Args:
        state:      Shared LangGraph workflow state.
        action_key: Key in ACTION_CONFIGS (e.g. "assess_risk").

    Returns:
        Updated state dict.

    Fail Fast Rule:
        If state["error"] is already set → skip immediately, return state unchanged.
        If this call fails → set state["error"] = message, return state.
    """
    # ── Fail Fast: previous node already failed ───────────────────────
    if state.get("error"):
        state.setdefault("logs", []).append(
            f"    [{action_key}] ⏭ SKIPPED — previous error: {state[\'error\']}"
        )
        return state

    cfg = ACTION_CONFIGS.get(action_key)
    if not cfg:
        state["error"] = f"{action_key}: no config found in ACTION_CONFIGS"
        state.setdefault("logs", []).append(f"    [{action_key}] ✗ {state[\'error\']}")
        return state

    url          = cfg.get("url", "")
    method       = cfg.get("method", "POST").upper()
    path_params  = cfg.get("path_params") or []
    query_params = cfg.get("query_params") or []
    header_params= cfg.get("header_params") or []
    body_params  = cfg.get("body_params") or {}

    ctx = _build_context(state)

    # ── Resolve :path_params ──────────────────────────────────────────
    for p in path_params:
        if not isinstance(p, dict) or "key" not in p:
            continue
        val = _resolve_value(p.get("value"), p["key"], ctx)
        url = url.replace(f":{p[\'key\']}", str(val) if val is not None else "")

    # ── Query string ──────────────────────────────────────────────────
    params: dict = {}
    for q in query_params:
        if not isinstance(q, dict) or "key" not in q:
            continue
        params[q["key"]] = _resolve_value(q.get("value"), q["key"], ctx)

    # ── Headers ───────────────────────────────────────────────────────
    headers: dict = {}
    for h in header_params:
        if not isinstance(h, dict) or "key" not in h:
            continue
        headers[h["key"]] = _resolve_value(h.get("value"), h["key"], ctx)

    # ── JSON body ─────────────────────────────────────────────────────
    # body_params is a dict {field: default_value}
    # Values are resolved from runtime context first; fallback to defaults.
    json_body: dict = {}
    if isinstance(body_params, dict):
        for field, default in body_params.items():
            json_body[field] = _resolve_value(default, field, ctx)
        # Inject any extra context fields not explicitly declared
        for ck, cv in ctx.items():
            if ck not in json_body:
                json_body[ck] = cv
    elif isinstance(body_params, list):
        for b in body_params:
            if isinstance(b, dict) and "key" in b:
                json_body[b["key"]] = _resolve_value(b.get("value"), b["key"], ctx)

    state.setdefault("logs", []).append(f"    [{action_key}] {method} {url}")
    state.setdefault("node_responses", {})

    # ── Execute HTTP Request ──────────────────────────────────────────
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.request(
                method=method,
                url=url,
                params=params if params else None,
                headers=headers if headers else None,
                json=json_body if method in ("POST", "PUT", "PATCH") else None,
            )
            response.raise_for_status()

        result = response.json() if response.text else {}
        state["logs"].append(f"    [{action_key}] ✓ {response.status_code}")
        state["last_result"]               = result
        state["http_response"]             = {"status_code": response.status_code, "url": str(response.url)}
        state["node_responses"][action_key] = result
        state["error"]                     = None   # clear any previous transient error

    except Exception as e:
        error_msg = f"{action_key} failed: {e}"
        state["logs"].append(f"    [{action_key}] ✗ {error_msg}")
        state["error"]                     = error_msg
        state["node_responses"][action_key] = {"error": error_msg}

    return state
'''


# ─── utils.py Template ────────────────────────────────────────────────────────
UTILS_PY = '''\
"""
utils.py — Shared logging helper for this LangGraph workflow.
"""
from __future__ import annotations
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
'''


# ─── langgraph_workflow.py Template Header ────────────────────────────────────
LANGGRAPH_WORKFLOW_PY_HEADER = '''\
"""
langgraph_workflow.py — Auto-generated LangGraph workflow.

DO NOT edit this file manually — regenerate from Tensaw Skill Studio.

Architecture:
  - action_configs.py : full API config per action (url, method, all params)
  - helpers.py        : run_api_node(state, action_key) — single shared caller
  - Each node fn      : calls ONLY run_api_node(state, "action_key"), returns state
  - Fail Fast         : if state["error"] is set, all subsequent nodes skip
"""
from __future__ import annotations
from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
from helpers import run_api_node


# ─── Shared Workflow State ────────────────────────────────────────────────────
class WorkflowState(TypedDict, total=False):
    """
    Mutable state passed through every node.

    error = None   → OK, graph continues normally
    error = "msg"  → FAIL FAST, all remaining nodes immediately skip
    """
    last_result:      Any
    http_response:    Any
    saved_data:       Any
    final_reply:      str
    condition_result: str
    logs:             list[str]
    node_responses:   dict[str, Any]
    error:            str | None


'''

# ─── Node Function Templates ──────────────────────────────────────────────────
LANGGRAPH_NODE_FN_ACTION = '''\
def {fn_name}(state: WorkflowState) -> WorkflowState:
    """Node: {label} — calls run_api_node(state, "{action_key}")"""
    return run_api_node(state, "{action_key}")


'''

LANGGRAPH_NODE_FN_START = '''\
def {fn_name}(state: WorkflowState) -> WorkflowState:
    """Node: {label} — workflow entry point (pass-through, no API call)"""
    state.setdefault("logs", []).append("[START] Workflow entered")
    state.setdefault("node_responses", {{}})
    if "error" not in state:
        state["error"] = None
    return state


'''

LANGGRAPH_NODE_FN_PASSTHROUGH = '''\
def {fn_name}(state: WorkflowState) -> WorkflowState:
    """Node: {label} — pass-through (no API action configured)"""
    state.setdefault("logs", []).append("[PASS] {label}")
    return state


'''

# ─── Graph Builder Blocks ─────────────────────────────────────────────────────
LANGGRAPH_BUILDER_HEADER = '''\
# ─── Graph Construction ───────────────────────────────────────────────────────
builder = StateGraph(WorkflowState)

'''

LANGGRAPH_ADD_NODE      = 'builder.add_node("{lg_name}", {fn_name})\n'
LANGGRAPH_SET_ENTRY     = 'builder.set_entry_point("{root}")\n'
LANGGRAPH_ADD_EDGE      = 'builder.add_edge("{source}", "{target}")\n'
LANGGRAPH_TERMINAL_EDGE = 'builder.add_edge("{leaf}", END)\n'
LANGGRAPH_ADD_CONDITIONAL_COMMENT = '# Conditional: {source} → {target} if condition_result == "{value}"\n'
LANGGRAPH_FOOTER        = '\ngraph = builder.compile()\n'


# ─── main.py Template ─────────────────────────────────────────────────────────
MAIN_PY = '''\
"""
main.py — Entry point to execute this LangGraph workflow.

Usage:
    python main.py
"""
from langgraph_workflow import graph, WorkflowState


def run(initial_input: dict | None = None) -> WorkflowState:
    """
    Run the workflow with optional initial context data.

    initial_input is injected into state["saved_data"] and is available
    to all nodes for resolving path params, query params, and body params.

    Example:
        run({"case_id": "1", "claim_id": "123"})
    """
    initial_state: WorkflowState = {
        "logs":             [],
        "last_result":      None,
        "http_response":    None,
        "saved_data":       initial_input or {},
        "final_reply":      "",
        "condition_result": "",
        "node_responses":   {},
        "error":            None,
    }
    config = {"configurable": {"thread_id": "default_session"}}
    final_state = graph.invoke(initial_state, config=config)

    status = "✅ Complete" if not final_state.get("error") else "❌ Failed"
    print(f"\\n{status}")
    print(f"  Error        : {final_state.get(\'error\')}")
    print(f"  Last Result  : {final_state.get(\'last_result\')}")
    print(f"  HTTP         : {final_state.get(\'http_response\')}")
    print("\\n  Execution Logs:")
    for line in final_state.get("logs", []):
        print(f"    {line}")
    return final_state


if __name__ == "__main__":
    # ↓ Provide your runtime context here
    run(initial_input={
        "case_id":  "1",
        "claim_id": "123",
    })
'''


# ─── requirements.txt Template ───────────────────────────────────────────────
REQUIREMENTS_TXT = '''\
langgraph>=0.2.0
langchain-core>=0.1.0
httpx>=0.27.0
pydantic>=2.0.0
typing_extensions>=4.9.0
'''


# ─── README.md Template ──────────────────────────────────────────────────────
README_MD = '''\
# {workflow_name} — LangGraph Workflow

Auto-generated by **Tensaw Skill Studio**.

---

## 📁 File Structure

| File | Purpose |
|------|---------|
| `action_configs.py` | Full API config per action — edit here to change URLs or params |
| `helpers.py` | `run_api_node(state, action_key)` — single shared HTTP caller |
| `utils.py` | Logging helper |
| `langgraph_workflow.py` | Node functions + graph wiring |
| `main.py` | Entry point with runtime input example |
| `requirements.txt` | Python dependencies |

---

## 🏗️ Architecture

```
main.py  →  graph.invoke(state)
              └── start  →  node_a  →  node_b  →  ...  →  END
                               │
                               └── run_api_node(state, "action_key")
                                        │
                                        ├── ACTION_CONFIGS["action_key"]
                                        │       url, method, path/query/header/body params
                                        │
                                        ├── resolves :path_params from state context
                                        ├── resolves body fields from state context
                                        └── on error: state["error"] = msg  ← FAIL FAST
```

**Fail Fast:** If any node sets `state["error"]`, all subsequent nodes are skipped immediately.

---

## 🔗 Workflow Nodes ({node_count} nodes)

{node_table}

---

## 🌐 API Endpoints Called

{endpoint_table}

---

## 🔄 How to Run from Python

```python
from langgraph_workflow import graph, WorkflowState

state: WorkflowState = {{
    "logs":           [],
    "last_result":    None,
    "saved_data":     {{"case_id": "1", "claim_id": "123"}},
    "node_responses": {{}},
    "error":          None,
}}
result = graph.invoke(state, config={{"configurable": {{"thread_id": "my_session"}}}})
print(result["last_result"])
```

---

*Generated by Tensaw Skill Studio — Do not edit manually.*
'''
