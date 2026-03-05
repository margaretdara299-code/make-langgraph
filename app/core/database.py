"""
SQLite database — SQLAlchemy engine, session factory, and dependency injection.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from app.core.config import db_config

engine = create_engine(
    f"sqlite:///{db_config.PATH}",
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
)


@event.listens_for(engine, "connect")
def _configure_new_connection(dbapi_connection, connection_record):
    """Configure each new SQLite connection."""
    dbapi_connection.execute("PRAGMA foreign_keys = ON;")
    dbapi_connection.execute("PRAGMA journal_mode = WAL;")
    dbapi_connection.execute("PRAGMA busy_timeout = 5000;")


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db_session():
    """FastAPI dependency — yields a Session, auto-commits or rollbacks."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
