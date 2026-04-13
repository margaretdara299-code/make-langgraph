"""
compiler/sanitizer.py — Deterministic LangGraph node naming from ReactFlow IDs.
Converts free-form labels into unique, valid Python snake_case identifiers.
"""
from __future__ import annotations
import re
import unicodedata
from typing import Dict, Iterable, Tuple


def sanitize_identifier(raw: str) -> str:
    """Convert a free-form node label into a safe snake_case Python identifier."""
    normalized = unicodedata.normalize("NFKD", (raw or "").strip())
    ascii_only  = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned     = re.sub(r"[^A-Za-z0-9\s._-]", "", ascii_only)
    snake       = re.sub(r"[\s._-]+", "_", cleaned)
    snake       = re.sub(r"_+", "_", snake).strip("_").lower()

    if not snake:
        snake = "unnamed_node"
    if snake[0].isdigit():
        snake = f"node_{snake}"

    return snake


def build_unique_node_names(
    name_inputs: Iterable[Tuple[str, str]],
) -> Dict[str, str]:
    """
    Return a mapping of ReactFlow node-id → unique LangGraph node-name.

    Deduplicates by appending a short suffix from the original node ID
    when two nodes produce the same sanitized name.
    """
    result: Dict[str, str] = {}
    used: set[str] = set()

    for reactflow_id, raw_label in name_inputs:
        base = sanitize_identifier(raw_label)
        name = base

        if name in used:
            suffix = re.sub(r"[^A-Za-z0-9]", "", reactflow_id)[-8:].lower() or "dup"
            name = f"{base}_{suffix}"

        used.add(name)
        result[reactflow_id] = name

    return result
