"""
Pydantic request and response schemas for the Action Catalog feature.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field, field_validator

from app.common.constants import ACTION_CAPABILITIES, ACTION_KEY_RE


# =========================================================================
# Create / Update / Publish
# =========================================================================
class CreateActionDefinitionRequest(BaseModel):
    """Payload to create a new Action Definition in the catalog."""
    name: str
    action_key: str
    description: str | None = Field(default=None, max_length=400)
    category: str | None = None
    capability: str
    icon: str | None = None
    default_node_title: str
    scope: Literal["global", "client"] = "global"
    client_id: str | None = None

    # ── Version-level JSON blobs (populated by wizard steps 2–7) ──
    inputs_schema_json: Dict[str, Any] | List[Dict[str, Any]] | None = None
    execution_json: Dict[str, Any] | None = None
    outputs_schema_json: Dict[str, Any] | List[Dict[str, Any]] | None = None
    configurations_json: List[Dict[str, Any]] | None = None
    ui_form_json: Dict[str, Any] | None = None
    policy_json: Dict[str, Any] | None = None



    @field_validator("capability")
    @classmethod
    def validate_capability(cls, value: str) -> str:
        normalised = value.strip().upper()
        if normalised not in ACTION_CAPABILITIES:
            raise ValueError("invalid capability")
        return normalised

class UpdateActionDefinitionRequest(BaseModel):
    """Payload to update an action definition's metadata."""
    name: str | None = None
    description: str | None = Field(default=None, max_length=400)
    category: str | None = None
    capability: str | None = None
    icon: str | None = None
    default_node_title: str | None = None


class UpdateActionVersionRequest(BaseModel):
    """Payload to update a draft action version's schemas."""
    inputs_schema_json: Dict[str, Any] | List[Dict[str, Any]] | None = None
    execution_json: Dict[str, Any] | None = None
    outputs_schema_json: Dict[str, Any] | List[Dict[str, Any]] | None = None
    configurations_json: List[Dict[str, Any]] | None = None
    ui_form_json: Dict[str, Any] | None = None
    policy_json: Dict[str, Any] | None = None


class PublishActionRequest(BaseModel):
    """Payload to publish a draft action version."""
    release_notes: str | None = None


class CreateDraftFromPublishedRequest(BaseModel):
    """Payload to create a new draft from a published action version."""
    from_version_id: str


# =========================================================================
# Responses
# =========================================================================
class DesignerActionsResponse(BaseModel):
    """Actions available in the Skill Designer left rail."""
    items: List[Dict[str, Any]]
