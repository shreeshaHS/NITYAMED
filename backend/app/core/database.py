"""SQLAlchemy 2.x engine, session management, and declarative base."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Shared SQLAlchemy declarative base for all domain modules."""


def build_engine(database_url: str):
    """Create a SQLAlchemy engine configured for SQLite or PostgreSQL."""
    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )
    return create_engine(database_url, pool_pre_ping=True)


settings = get_settings()
engine = build_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session per request and ensure cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
