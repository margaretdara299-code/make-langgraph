from sqlalchemy.orm import Session
from app.connector import repository as repo
from app.logger.logging import logger


def get_all_connectors(db: Session, is_active: bool | None = None) -> list:
    """List all connectors."""
    return repo.fetch_all_connectors(db, is_active=is_active)


def get_connector(db: Session, connector_id: int) -> dict | None:
    """Retrieve a single connector."""
    return repo.fetch_connector_by_id(db, connector_id)


def create_connector(db: Session, request) -> dict:
    """Business logic for creating a connector."""
    logger.debug(f"Creating connector: {request.name} (type={request.connector_type})")
    return repo.create_connector(db, request)


def update_connector(db: Session, connector_id: int, request) -> dict:
    """Business logic for updating a connector."""
    logger.debug(f"Updating connector: {connector_id}")
    return repo.update_connector(db, connector_id, request)


def delete_connector(db: Session, connector_id: int) -> bool:
    """Business logic for deleting a connector."""
    logger.debug(f"Attempting to delete connector: {connector_id}")
    return repo.delete_connector(db, connector_id)
