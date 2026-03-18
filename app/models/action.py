"""
Pydantic request and response schemas for the Action Catalog feature.
"""
from __future__ import annotations
from typing import Any, Dict, List
from pydantic import BaseModel, Field


# =========================================================================
# Create Action
# =========================================================================
class CreateActionDefinitionRequest(BaseModel):
    """Payload to create a new Action."""
    name: str
    action_key: str
    description: str | None = Field(default=None, max_length=400)
    category_id: int | None = None
    capability_id: int | None = None
    icon: str | None = None
    default_node_title: str | None = None
    scope: str | None = "global"
    client_id: str | None = "1"
    status: str | None = "published"
    is_active: bool = True

    # ── JSON blobs ──
    inputs_schema_json: Dict[str, Any] | List[Any] | None = None
    execution_json: Dict[str, Any] | List[Any] | None = None
    outputs_schema_json: Dict[str, Any] | List[Any] | None = None
    configurations_json: Dict[str, Any] | List[Any] | None = None
    ui_form_json: Dict[str, Any] | List[Any] | None = None
    policy_json: Dict[str, Any] | List[Any] | None = None

# =========================================================================
# Update Action
# =========================================================================
class UpdateActionDefinitionRequest(BaseModel):
    """Payload to update an action (definition + JSON blobs)."""
    name: str | None = None
    action_key: str | None = None
    description: str | None = Field(default=None, max_length=400)
    category_id: int | None = None
    capability_id: int | None = None
    icon: str | None = None
    default_node_title: str | None = None
    scope: str | None = None
    status: str | None = None       # "draft" or "published"
    is_active: bool | None = None   # true or false

    # ── JSON blobs ──
    inputs_schema_json: Dict[str, Any] | List[Any] | None = None
    execution_json: Dict[str, Any] | List[Any] | None = None
    outputs_schema_json: Dict[str, Any] | List[Any] | None = None
    configurations_json: Dict[str, Any] | List[Any] | None = None
    ui_form_json: Dict[str, Any] | List[Any] | None = None
    policy_json: Dict[str, Any] | List[Any] | None = None


# =========================================================================
# Update Action Status only
# =========================================================================
class UpdateActionStatusRequest(BaseModel):
    """Payload to only toggle an action's draft/publish status or active state."""
    status: str | None = None       # "draft" or "published"
    is_active: bool | None = None   # true or false
