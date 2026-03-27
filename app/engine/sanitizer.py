"""
Sanitization helpers for deterministic LangGraph node naming.
Ported from reference implementation for consistency.
"""
from __future__ import annotations
import re
import unicodedata
from typing import Dict, Iterable, Tuple


def sanitize_identifier_base(raw_value: str) -> str:
    """Convert a free-form node-name source into a safe snake_case identifier."""

    normalized_value = unicodedata.normalize("NFKD", (raw_value or "").strip())
    ascii_value = normalized_value.encode("ascii", "ignore").decode("ascii")
    cleaned_value = re.sub(r"[^A-Za-z0-9\s._-]", "", ascii_value)
    snake_case_value = re.sub(r"[\s._-]+", "_", cleaned_value)
    snake_case_value = re.sub(r"_+", "_", snake_case_value).strip("_").lower()

    if not snake_case_value:
        snake_case_value = "unnamed_node"

    if snake_case_value[0].isdigit():
        snake_case_value = f"node_{snake_case_value}"

    return snake_case_value


def build_unique_node_names(
    name_inputs: Iterable[Tuple[str, str]],
) -> Dict[str, str]:
    """Return a ReactFlow node-id -> unique LangGraph node-name mapping."""

    node_name_by_reactflow_id: Dict[str, str] = {}
    used_node_names: set[str] = set()

    for reactflow_node_id, raw_name_source in name_inputs:
        base_node_name = sanitize_identifier_base(raw_name_source)
        unique_node_name = base_node_name

        if unique_node_name in used_node_names:
            short_suffix = re.sub(r"[^A-Za-z0-9]", "", reactflow_node_id)[-8:].lower()
            unique_node_name = f"{base_node_name}_{short_suffix or 'dup'}"

        used_node_names.add(unique_node_name)
        node_name_by_reactflow_id[reactflow_node_id] = unique_node_name

    return node_name_by_reactflow_id
