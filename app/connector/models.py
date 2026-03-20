"""
Pydantic schemas for the Enterprise Connectivity Validation Service.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel, Field, field_validator
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


class ConnectivityValidationRequest(BaseModel):
    """Enterprise-grade request for verifying data source connectivity."""
    engine: Literal["mysql", "postgresql", "sqlserver"] = Field(..., description="Database engine type")
    host: str = Field(..., example="127.0.0.1")
    port: int = Field(..., ge=1, le=65535, example=3306)
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    database: str = Field(..., min_length=1)

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Host cannot be empty or whitespace")
        return v.strip()


class ConnectivityMetadata(BaseModel):
    """Rich metadata about the validated connection."""
    server_version: str | None = None
    current_user: str | None = None
    latency_ms: float
    message: str


class ConnectivityValidationResponse(BaseModel):
    """Result of the connectivity verification check."""
    status: bool = Field(..., description="True if connection was successful")
    details: ConnectivityMetadata | None = None
    error_type: str | None = None
    error_message: str | None = None
