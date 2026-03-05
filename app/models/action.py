"""
Pydantic request and response schemas for the Action Catalog feature.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.common.constants import ACTION_CAPABILITIES, ACTION_KEY_RE


# =========================================================================
# Create / Update / Publish
# =========================================================================
class CreateActionDefinitionRequest(BaseModel):
    """Payload to create a new Action Definition in the catalog."""
    name: str
    action_key: str
    description: Optional[str] = Field(default=None, max_length=400)
    category: Optional[str] = None
    capability: str
    icon: Optional[str] = None
    default_node_title: str
    scope: Literal["global", "client"] = "global"
    client_id: Optional[str] = None

    @field_validator("action_key")
    @classmethod
    def validate_action_key(cls, value: str) -> str:
        trimmed = value.strip()
        if not ACTION_KEY_RE.match(trimmed):
            raise ValueError("action_key must be lowercase dot notation")
        return trimmed

    @field_validator("capability")
    @classmethod
    def validate_capability(cls, value: str) -> str:
        normalised = value.strip().upper()
        if normalised not in ACTION_CAPABILITIES:
            raise ValueError("invalid capability")
        return normalised


class UpdateActionVersionRequest(BaseModel):
    """Payload to update a draft action version's schemas."""
    inputs_schema_json: Optional[Dict[str, Any]] = None
    execution_json: Optional[Dict[str, Any]] = None
    outputs_schema_json: Optional[Dict[str, Any]] = None
    ui_form_json: Optional[Dict[str, Any]] = None
    policy_json: Optional[Dict[str, Any]] = None


class PublishActionRequest(BaseModel):
    """Payload to publish a draft action version."""
    release_notes: Optional[str] = None


class CreateDraftFromPublishedRequest(BaseModel):
    """Payload to create a new draft from a published action version."""
    from_version_id: str


# =========================================================================
# Responses
# =========================================================================
class DesignerActionsResponse(BaseModel):
    """Actions available in the Skill Designer left rail."""
    items: List[Dict[str, Any]]
