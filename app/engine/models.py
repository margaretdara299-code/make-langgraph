"""
Pydantic models and TypedDict for the workflow JSON schema and LangGraph state.
"""
from __future__ import annotations
from typing import Any, TypedDict
from pydantic import BaseModel, Field, AliasChoices

# ─── LangGraph shared state ────────────────────────────────────────────
class WorkflowState(TypedDict, total=False):
    """
    Mutable state dict carried through every node in the graph.

    LangGraph rules:
      - error = None  → no error, graph continues
      - error = "msg" → node failed, all subsequent nodes skip (Fail Fast)
      - Each node only reads/writes its own fields, then returns state.
    """
    last_result:      Any
    http_response:    Any
    saved_data:       Any
    final_reply:      str
    condition_result: str           # "true" | "false"
    logs:             list[str]
    node_responses:   dict[str, Any]
    error:            str | None    # None = OK, any string = FAIL FAST


# ─── Workflow JSON shapes (Aligned with DB SkillGraphNode/Connection) ───
class ActionData(BaseModel):
    """Corresponds to node.data in the React Flow / DB format."""
    actionKey:  str | None = Field(None, alias="action_key")
    capability: str | None = None
    config:     dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("configurationsJson", "configurations_json", "config")
    )
    label: str | None = None

    model_config = {"populate_by_name": True}


class NodeDef(BaseModel):
    """Corresponds to SkillGraphNode in app/models/skill.py."""
    id:   str
    type: str | None = "action"
    data: ActionData = Field(default_factory=ActionData)


class EdgeDef(BaseModel):
    """Corresponds to SkillGraphConnection in app/models/skill.py."""
    id:         str | None = None
    source:     str
    target:     str
    condition:  dict[str, Any] = Field(default_factory=dict)
    is_default: bool = Field(False, alias="is_default")

    model_config = {"populate_by_name": True}


class WorkflowDef(BaseModel):
    """The full container stored in the database."""
    nodes:       list[NodeDef]       = Field(default_factory=list)
    connections: dict[str, EdgeDef]  = Field(default_factory=dict)
