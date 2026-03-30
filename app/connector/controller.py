"""
Connector Controller — API routes for managing external system integrations.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db_session
from app.common.response import build_success_response, raise_internal_server_error, raise_not_found, raise_bad_request
from app.connector import service as connector_service
from app.connector.models import CreateConnectorRequest, UpdateConnectorRequest, ConnectorResponse, ConnectivityValidationRequest
from app.connector.connectivity_service import verify_connectivity
from app.logger.logging import logger

router = APIRouter(prefix="/connectors", tags=["Connectors"])



@router.post("/connectivity/verify")
def verify_connectivity_endpoint(request: ConnectivityValidationRequest):
    """
    Enterprise Connectivity Validation.
    Verifies database credentials and returns rich metadata (latency, version).
    """
    result = verify_connectivity(request)
    if result.status:
        return build_success_response("Connectivity verified successfully.", result.details)
    else:
        # Return 200 with status=False or 500? 
        # Usually, connectivity failure is a valid business response, but here we use 500 to trigger "error" in UI
        raise_internal_server_error(result.error_message)


@router.post("", status_code=201)
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


@router.get("")
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


@router.get("/grouped")
def list_connectors_grouped(
    db: Session = Depends(get_db_session)
):
    """List all connectors grouped by their connector type (e.g., DATABASE, API)."""
    logger.debug("API: Fetching connectors grouped by type")
    try:
        grouped_connectors_map = connector_service.get_connectors_grouped(db)
        return build_success_response("Connectors grouped by type fetched successfully", grouped_connectors_map)
    except Exception:
        logger.exception("Error fetching grouped connectors")
        raise_internal_server_error()


@router.get("/{connector_id}")
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


@router.patch("/{connector_id}")
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


@router.delete("/{connector_id}")
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
