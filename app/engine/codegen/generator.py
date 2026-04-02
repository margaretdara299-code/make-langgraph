"""
Code Generator — converts a WorkflowDef into a multi-file deployable LangGraph project.

Returns a dictionary mapping smart filenames to their generated source code:
    {
        "utils.py":               shared logging/utility helpers,
        "helpers.py":             generic HTTPX action executor,
        "langgraph_workflow.py":  auto-generated LangGraph graph,
        "main.py":                local entry point,
        "requirements.txt":       pip dependencies,
        "README.md":              usage documentation,
    }
"""
from __future__ import annotations

from app.engine.models import WorkflowDef
from app.engine.compiler.sanitizer import build_unique_node_names
from app.engine.codegen import templates as tmpl


def generate_project_files(workflow_data: dict, workflow_name: str = "Workflow") -> dict[str, str]:
    """
    Generate a complete, deployable LangGraph project from a workflow definition.

    Args:
        workflow_data:  Dict with 'nodes' and 'connections' keys (DB format).
        workflow_name:  Human-readable name embedded in the README.

    Returns:
        Dict mapping filename → source code (or content).
    """
    wf = WorkflowDef(**workflow_data)

    # Build unique sanitized LangGraph node names
    name_inputs = [(n.id, n.data.actionKey or n.data.label or n.id) for n in wf.nodes]
    id_map = build_unique_node_names(name_inputs)

    # ── Build langgraph_workflow.py ─────────────────────────────────────
    workflow_lines: list[str] = [tmpl.LANGGRAPH_WORKFLOW_PY_HEADER]

    # Node functions
    for node in wf.nodes:
        lg_id   = id_map[node.id]
        fn_name = f"node_{lg_id}"
        label   = node.data.label or lg_id
        action_key = node.data.actionKey or ""
        config  = node.data.config or {}

        if action_key and config.get("url"):
            # Render config as a proper Python dict literal
            config_repr = _build_dict_repr(config)
            workflow_lines.append(
                tmpl.LANGGRAPH_NODE_FN_TEMPLATE.format(
                    fn_name=fn_name,
                    label=label,
                    action_key=action_key,
                    config_repr=config_repr,
                )
            )
        else:
            workflow_lines.append(
                tmpl.LANGGRAPH_PASSTHROUGH_FN_TEMPLATE.format(
                    fn_name=fn_name,
                    label=label,
                )
            )

    # Builder block
    workflow_lines.append(tmpl.LANGGRAPH_BUILDER_HEADER)

    for node in wf.nodes:
        lg_id   = id_map[node.id]
        fn_name = f"node_{lg_id}"
        workflow_lines.append(tmpl.LANGGRAPH_ADD_NODE.format(lg_name=lg_id, fn_name=fn_name))

    workflow_lines.append("\n")

    # Entry point
    if wf.nodes:
        root = id_map[wf.nodes[0].id]
        workflow_lines.append(tmpl.LANGGRAPH_SET_ENTRY.format(root=root))

    # Edges
    conditional_sources: set[str] = set()
    for edge in wf.connections.values():
        src = id_map[edge.source]
        tgt = id_map[edge.target]
        cond_value = (edge.condition or {}).get("value")

        if cond_value in ("true", "false") and not edge.is_default:
            workflow_lines.append(
                tmpl.LANGGRAPH_ADD_CONDITIONAL_COMMENT.format(
                    source=src, target=tgt, value=cond_value
                )
            )
            conditional_sources.add(src)

        workflow_lines.append(tmpl.LANGGRAPH_ADD_EDGE.format(source=src, target=tgt))

    # Terminal → END edges
    sources_set = {id_map[e.source] for e in wf.connections.values()}
    for node in wf.nodes:
        lg_id = id_map[node.id]
        if lg_id not in sources_set:
            workflow_lines.append(tmpl.LANGGRAPH_TERMINAL_EDGE.format(leaf=lg_id))

    workflow_lines.append(tmpl.LANGGRAPH_FOOTER)
    workflow_py = "".join(workflow_lines)

    # ── Build README.md ─────────────────────────────────────────────────
    node_rows = "\n".join(
        f"| `{id_map[n.id]}` | {n.data.label or n.id} | `{n.type or 'action'}` |"
        for n in wf.nodes
    )
    node_table = "| Node Name | Label | Type |\n|-----------|-------|------|\n" + node_rows

    endpoint_rows = []
    for n in wf.nodes:
        url = (n.data.config or {}).get("url")
        method = (n.data.config or {}).get("method", "GET")
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
        "utils.py":               tmpl.UTILS_PY,
        "helpers.py":             tmpl.HELPERS_PY,
        "langgraph_workflow.py":  workflow_py,
        "main.py":                tmpl.MAIN_PY,
        "requirements.txt":       tmpl.REQUIREMENTS_TXT,
        "README.md":              readme,
    }


def _build_dict_repr(config: dict) -> str:
    """Render a config dict as a clean Python dict literal for embedding in source code."""
    lines = ["{"]
    for k, v in config.items():
        if isinstance(v, str):
            v_repr = f'"{v}"'
        elif isinstance(v, list):
            v_repr = repr(v)
        elif isinstance(v, bool):
            v_repr = "True" if v else "False"
        elif v is None:
            v_repr = "None"
        else:
            v_repr = repr(v)
        lines.append(f'    "{k}": {v_repr},')
    lines.append("}")
    return "\n".join(lines)
