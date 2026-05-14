"""SQLAlchemy engine and session factory for Scenario Analyzer."""

from collections.abc import Generator
from contextlib import contextmanager
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db_models import Base

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def reset_engine() -> None:
    """Dispose engine and clear cached factory (for tests)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        url = (settings.DATABASE_URL or "").strip() or "sqlite:///./scenario_analyzer.db"
        connect_args: dict = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_engine(url, connect_args=connect_args, echo=False)
        logger.info("SQLAlchemy engine created for URL prefix: %s", url.split("://")[0])
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _SessionLocal


def init_db() -> None:
    """Create all tables if they do not exist."""
    Base.metadata.create_all(bind=get_engine())


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
