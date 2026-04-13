"""
Code Generator — converts a WorkflowDef into a multi-file deployable LangGraph project.

Generated file structure:
    {
        "utils.py":              logging helper,
        "helpers.py":            run_api_node(state, action_key) — single shared caller,
        "action_configs.py":     full DB config per action (url/method/all params),
        "langgraph_workflow.py": node functions + graph wiring,
        "main.py":               entry point with runtime input example,
        "requirements.txt":      pip dependencies,
        "README.md":             architecture + usage documentation,
    }

Design rules in generated code:
    1. action_configs.py — mirrors DB exactly: url, method, path/query/header/body params
    2. run_api_node(state, action_key) — resolves all params from context, calls API
    3. Each node function: ONLY calls run_api_node(state, "action_key"), returns state
    4. Fail Fast — state["error"] set on failure → all next nodes skip immediately
    5. start node — pass-through entry point (no API call, just logs)
"""
from __future__ import annotations

from app.engine.models import WorkflowDef
from app.engine.compiler.sanitizer import build_unique_node_names
from app.engine.codegen import templates as tmpl


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _safe_repr(value) -> str:
    """
    Render a Python value as a clean, readable Python literal for source embedding.
    Handles: str, int, float, bool, None, list, dict.
    """
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, list):
        if not value:
            return "[]"
        items = [f"        {_safe_repr(item)}" for item in value]
        return "[\n" + ",\n".join(items) + "\n    ]"
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = []
        for k, v in value.items():
            lines.append(f"            {repr(k)}: {_safe_repr(v)}")
        return "{\n" + ",\n".join(lines) + "\n        }"
    return repr(value)


# ─── Main entry point ─────────────────────────────────────────────────────────

def generate_project_files(workflow_data: dict, workflow_name: str = "Workflow") -> dict[str, str]:
    """
    Generate a complete, deployable LangGraph project from a workflow definition.

    Args:
        workflow_data:  Dict with 'nodes' and 'connections' keys (DB format).
        workflow_name:  Human-readable name embedded in the README.

    Returns:
        Dict mapping filename → source code.
    """
    wf = WorkflowDef(**workflow_data)

    # Build unique sanitized LangGraph node names
    name_inputs = [(n.id, n.data.actionKey or n.data.label or n.id) for n in wf.nodes]
    id_map = build_unique_node_names(name_inputs)

    # ── 1. action_configs.py — full DB config per action node ─────────────────
    action_cfg_lines: list[str] = [tmpl.ACTION_CONFIGS_PY_HEADER]

    for node in wf.nodes:
        if node.type == "start":
            continue  # start node has no API config

        action_key = node.data.actionKey
        if not action_key:
            continue

        config       = node.data.config or {}
        url          = config.get("url", "")
        method       = config.get("method", "POST").upper()
        path_params  = config.get("path_params") or []
        query_params = config.get("query_params") or []
        header_params= config.get("header_params") or []
        body_params  = config.get("body_params") or {}

        action_cfg_lines.append(
            tmpl.ACTION_CONFIGS_PY_ENTRY.format(
                action_key=action_key,
                url=url,
                method=method,
                path_params_repr=_safe_repr(path_params),
                query_params_repr=_safe_repr(query_params),
                header_params_repr=_safe_repr(header_params),
                body_params_repr=_safe_repr(body_params),
            )
        )

    action_cfg_lines.append(tmpl.ACTION_CONFIGS_PY_FOOTER)
    action_configs_py = "".join(action_cfg_lines)

    # ── 2. langgraph_workflow.py — header + node functions + graph builder ─────
    workflow_lines: list[str] = [tmpl.LANGGRAPH_WORKFLOW_PY_HEADER]

    # Node functions — each calls ONLY run_api_node(state, "action_key")
    for node in wf.nodes:
        lg_id      = id_map[node.id]
        fn_name    = f"node_{lg_id}"
        label      = node.data.label or lg_id
        action_key = node.data.actionKey
        config     = node.data.config or {}
        has_url    = bool(config.get("url"))

        if node.type == "start":
            workflow_lines.append(
                tmpl.LANGGRAPH_NODE_FN_START.format(fn_name=fn_name, label=label)
            )
        elif action_key and has_url:
            workflow_lines.append(
                tmpl.LANGGRAPH_NODE_FN_ACTION.format(
                    fn_name=fn_name,
                    label=label,
                    action_key=action_key,
                )
            )
        else:
            workflow_lines.append(
                tmpl.LANGGRAPH_NODE_FN_PASSTHROUGH.format(fn_name=fn_name, label=label)
            )

    # Graph builder block
    workflow_lines.append(tmpl.LANGGRAPH_BUILDER_HEADER)

    for node in wf.nodes:
        lg_id   = id_map[node.id]
        fn_name = f"node_{lg_id}"
        workflow_lines.append(tmpl.LANGGRAPH_ADD_NODE.format(lg_name=lg_id, fn_name=fn_name))

    workflow_lines.append("\n")

    # Entry point: prefer "start" type node, else first node
    start_node = next((n for n in wf.nodes if n.type == "start"), None)
    entry_node = start_node or wf.nodes[0]
    workflow_lines.append(tmpl.LANGGRAPH_SET_ENTRY.format(root=id_map[entry_node.id]))

    # Edges from connections
    sources_with_conditional: set[str] = set()
    for edge in wf.connections.values():
        src = id_map.get(edge.source)
        tgt = id_map.get(edge.target)
        if not src or not tgt:
            continue
        cond_value = (edge.condition or {}).get("value")
        if cond_value in ("true", "false") and not edge.is_default:
            workflow_lines.append(
                tmpl.LANGGRAPH_ADD_CONDITIONAL_COMMENT.format(
                    source=src, target=tgt, value=cond_value
                )
            )
            sources_with_conditional.add(src)
        workflow_lines.append(tmpl.LANGGRAPH_ADD_EDGE.format(source=src, target=tgt))

    # Terminal → END for leaf nodes
    sources_set = {id_map.get(e.source) for e in wf.connections.values() if id_map.get(e.source)}
    for node in wf.nodes:
        lg_id = id_map[node.id]
        if lg_id not in sources_set:
            workflow_lines.append(tmpl.LANGGRAPH_TERMINAL_EDGE.format(leaf=lg_id))

    workflow_lines.append(tmpl.LANGGRAPH_FOOTER)
    workflow_py = "".join(workflow_lines)

    # ── 3. README.md ──────────────────────────────────────────────────────────
    node_rows = "\n".join(
        f"| `{id_map[n.id]}` | {n.data.label or n.id} | `{n.type or 'action'}` |"
        for n in wf.nodes
    )
    node_table = "| Node Name | Label | Type |\n|-----------|-------|------|\n" + node_rows

    endpoint_rows = []
    for n in wf.nodes:
        cfg    = n.data.config or {}
        url    = cfg.get("url", "")
        method = cfg.get("method", "POST")
        if url:
            endpoint_rows.append(f"| `{n.data.label or n.id}` | `{method}` | `{url}` |")

    endpoint_table = (
        "| Node | Method | URL |\n|------|--------|-----|\n" + "\n".join(endpoint_rows)
        if endpoint_rows
        else "_No external HTTP endpoints configured._"
    )

    readme = tmpl.README_MD.format(
        workflow_name=workflow_name,
        node_count=len(wf.nodes),
        node_table=node_table,
        endpoint_table=endpoint_table,
    )

    return {
        "utils.py":              tmpl.UTILS_PY,
        "helpers.py":            tmpl.HELPERS_PY,
        "action_configs.py":     action_configs_py,
        "langgraph_workflow.py": workflow_py,
        "main.py":               tmpl.MAIN_PY,
        "requirements.txt":      tmpl.REQUIREMENTS_TXT,
        "README.md":             readme,
    }
