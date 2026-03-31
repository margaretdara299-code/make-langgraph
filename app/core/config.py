"""
Application settings loaded from environment variables using pydantic-settings.

All configuration is centralised here. Values come from the .env file
via env_prefix matching.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.logger.logging import logger


logger.debug("Loading application configuration from .env")


class DatabaseConfig(BaseSettings):
    """Database connection settings. Reads DB_* env vars."""
    PATH: str = "tensaw_skills_studio.sqlite"
    POOL_SIZE: int = 5

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class ClaimsDBConfig(BaseSettings):
    """MySQL claims database settings. Reads CLAIMS_DB_* env vars."""
    HOST: str = "54.211.59.215"
    USER: str = "af_user"
    PASSWORD: str = "prim1615test"
    DATABASE: str = "alloFactorV4"
    PORT: int = 3306
    POOL_SIZE: int = 5
    MAX_OVERFLOW: int = 10
    POOL_TIMEOUT: int = 30
    POOL_RECYCLE: int = 1800

    model_config = SettingsConfigDict(
        env_prefix="CLAIMS_DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class AppConfig(BaseSettings):
    """Application metadata. Reads APP_* env vars."""
    TITLE: str = "Tensaw Skills Studio API"
    VERSION: str = "0.3.0"

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class ServerConfig(BaseSettings):
    """Server and CORS settings. Reads HOST, PORT, RELOAD, CORS_ORIGINS."""
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    CORS_ORIGINS: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Instantiate settings
db_config = DatabaseConfig()
claims_db_config = ClaimsDBConfig()
app_config = AppConfig()
server_config = ServerConfig()
