"""
Application settings loaded from environment variables using pydantic-settings.

All configuration is centralised here. Values come from the .env file
via env_prefix matching.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.logger.logging import logger


logger.info("Loading application configuration from .env")


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
app_config = AppConfig()
server_config = ServerConfig()
