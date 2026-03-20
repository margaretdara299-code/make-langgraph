"""
Connectivity Service — enterprise-level database verification logic.
"""
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Protocol
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, OperationalError
from app.connector.models import ConnectivityValidationRequest, ConnectivityValidationResponse, ConnectivityMetadata
from app.logger.logging import logger

# =========================================================================
# Strategy Base
# =========================================================================

class DataSourceValidator(ABC):
    """Base interface for database-specific connectivity validation."""
    
    @abstractmethod
    def get_connection_url(self, request: ConnectivityValidationRequest) -> str:
        """Construct a valid SQLAlchemy connection URL."""
        pass

    @abstractmethod
    def get_metadata_query(self) -> str:
        """Query to fetch server version and current user."""
        pass

    def get_connect_args(self) -> dict:
        """Default connection arguments (timeouts)."""
        return {"connect_timeout": 5}


class MySQLValidator(DataSourceValidator):
    def get_connection_url(self, request: ConnectivityValidationRequest) -> str:
        return f"mysql+pymysql://{request.username}:{request.password}@{request.host}:{request.port}/{request.database}"
    
    def get_metadata_query(self) -> str:
        return "SELECT VERSION(), CURRENT_USER()"


class PostgresValidator(DataSourceValidator):
    def get_connection_url(self, request: ConnectivityValidationRequest) -> str:
        return f"postgresql+psycopg2://{request.username}:{request.password}@{request.host}:{request.port}/{request.database}"
    
    def get_metadata_query(self) -> str:
        return "SELECT version(), current_user"


class SQLServerValidator(DataSourceValidator):
    def get_connection_url(self, request: ConnectivityValidationRequest) -> str:
        # Note: requires ODBC driver installed on the system
        return f"mssql+pyodbc://{request.username}:{request.password}@{request.host}:{request.port}/{request.database}?driver=ODBC+Driver+17+for+SQL+Server"
    
    def get_metadata_query(self) -> str:
        return "SELECT @@VERSION, SUSER_SNAME()"
    
    def get_connect_args(self) -> dict:
        return {} # pyodbc uses timeout inside the connection string usually


# =========================================================================
# Main Service
# =========================================================================

def verify_connectivity(request: ConnectivityValidationRequest) -> ConnectivityValidationResponse:
    """Enterprise-level verification of data source connectivity."""
    
    validators = {
        "mysql": MySQLValidator(),
        "postgresql": PostgresValidator(),
        "sqlserver": SQLServerValidator()
    }
    
    validator = validators.get(request.engine)
    if not validator:
        return ConnectivityValidationResponse(
            status=False, 
            error_type="UnsupportedEngine", 
            error_message=f"No validator implemented for {request.engine}"
        )

    start_time = time.perf_counter()
    url = validator.get_connection_url(request)
    
    try:
        engine = create_engine(url, connect_args=validator.get_connect_args())
        
        with engine.connect() as conn:
            # Fetch metadata
            res = conn.execute(text(validator.get_metadata_query())).first()
            version, user = res[0], res[1]
            latency = (time.perf_counter() - start_time) * 1000 # convert to ms
            
            return ConnectivityValidationResponse(
                status=True,
                details=ConnectivityMetadata(
                    server_version=str(version),
                    current_user=str(user),
                    latency_ms=round(latency, 2),
                    message="Connectivity verified successfully."
                )
            )

    except OperationalError as e:
        # Categorize common errors
        msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        error_type = "NetworkFailure"
        if "Access denied" in msg or "authentication" in msg.lower():
            error_type = "AuthenticationFailure"
        elif "Unknown database" in msg or "does not exist" in msg:
            error_type = "DatabaseNotFound"
            
        logger.error(f"Connectivity check failed [{error_type}]: {msg}")
        return ConnectivityValidationResponse(
            status=False,
            error_type=error_type,
            error_message=msg
        )
    except Exception as e:
        logger.exception("Unexpected error during connectivity check")
        return ConnectivityValidationResponse(
            status=False,
            error_type="InternalError",
            error_message=str(e)
        )
