"""
FastAPI lifespan — startup and shutdown lifecycle management.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from app.core.database import engine
from app.core.schema import initialise_database
from app.seed import seed_demo_data
from app.logger.logging import logger


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup: init schema + seed. Shutdown: dispose engine."""
    logger.info("Application startup: initializing database.")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("SQLAlchemy DB connection pool initialized successfully.")
    except Exception as error:
        logger.error(f"Failed to initialize DB connection pool: {error}")

    initialise_database()
    seed_demo_data()
    yield
    engine.dispose()
    logger.info("Application shutdown complete.")
