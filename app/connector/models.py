"""
Pydantic request and response schemas for the Connector feature.
"""
from __future__ import annotations
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class CreateConnectorRequest(BaseModel):
    """Payload to create a new Connector."""
    name: str = Field(..., description="Display name of the connector")
    connector_type: str = Field(..., description="System type (e.g., 'jira', 'slack', 'database')")
    description: Optional[str] = Field(None, max_length=400)
    config_json: Dict[str, Any] = Field(default_factory=dict, description="Configuration and tokens")
    is_active: bool = True


class UpdateConnectorRequest(BaseModel):
    """Payload to update an existing Connector."""
    name: Optional[str] = None
    connector_type: Optional[str] = None
    description: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class ConnectorResponse(BaseModel):
    """Standard response envelope for a Connector."""
    connector_id: int
    name: str
    connector_type: str
    description: Optional[str] = None
    config_json: Dict[str, Any]
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
