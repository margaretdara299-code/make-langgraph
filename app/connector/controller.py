"""
Connector Controller — API routes for managing external system integrations.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db_session
from app.common.response import build_success_response, raise_internal_server_error, raise_not_found, raise_bad_request
from app.connector import service as connector_service
from app.connector.models import CreateConnectorRequest, UpdateConnectorRequest, ConnectorResponse
from app.logger.logging import logger

router = APIRouter(prefix="/api/v1", tags=["Connectors"])


@router.post("/connectors", status_code=201)
def create_connector(
    request: CreateConnectorRequest,
    db: Session = Depends(get_db_session)
):
    """Create a new connector with configuration."""
    try:
        result = connector_service.create_connector(db, request)
        return build_success_response("Connector created", result)
    except Exception:
        logger.debug("Error creating connector")
        raise_internal_server_error()


@router.get("/connectors")
def list_connectors(
    db: Session = Depends(get_db_session),
    active_only: bool | None = Query(None)
):
    """List all connectors."""
    try:
        result = connector_service.get_all_connectors(db, is_active=active_only)
        return build_success_response("Connectors fetched", result)
    except Exception:
        logger.exception("Error listing connectors")
        raise_internal_server_error()


@router.get("/connectors/{connector_id}")
def get_connector(
    connector_id: int,
    db: Session = Depends(get_db_session)
):
    """Get a single connector by ID."""
    try:
        result = connector_service.get_connector(db, connector_id)
        if not result:
            raise_not_found("Connector not found")
        return build_success_response("Connector fetched", result)
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Error fetching connector {connector_id}")
        raise_internal_server_error()


@router.patch("/connectors/{connector_id}")
def update_connector(
    connector_id: int,
    request: UpdateConnectorRequest,
    db: Session = Depends(get_db_session)
):
    """Update an existing connector's configuration."""
    try:
        result = connector_service.get_connector(db, connector_id)
        if not result:
            raise_not_found("Connector not found")
        
        updated = connector_service.update_connector(db, connector_id, request)
        return build_success_response("Connector updated", updated)
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Error updating connector {connector_id}")
        raise_internal_server_error()


@router.delete("/connectors/{connector_id}")
def delete_connector(
    connector_id: int,
    db: Session = Depends(get_db_session)
):
    """Delete a connector (only if not in use by any actions)."""
    try:
        result = connector_service.get_connector(db, connector_id)
        if not result:
            raise_not_found("Connector not found")
        
        success = connector_service.delete_connector(db, connector_id)
        if not success:
            raise_bad_request("Connector cannot be deleted: it is currently referenced by actions.")
            
        return build_success_response("Connector deleted")
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Error deleting connector {connector_id}")
        raise_internal_server_error()
