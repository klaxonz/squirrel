import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from infrastructure.config.settings import settings
from shared_kernel.infrastructure.log import init_logging

init_logging()
logger = logging.getLogger(__name__)
AFTER_COMMIT_CALLBACKS_KEY = "after_commit_callbacks"

db_config = {
    "host": settings.postgres.host,
    "port": settings.postgres.port,
    "user": settings.postgres.user,
    "password": settings.postgres.password,
    "database": settings.postgres.database,
}

engine = create_engine(
    settings.database_url,
    pool_size=settings.postgres.pool_size,
    max_overflow=settings.postgres.pool_max_size,
    pool_recycle=settings.postgres.pool_recycle,
    pool_pre_ping=True,  # 检测失效连接
    pool_use_lifo=True,  # LIFO 池,提高连接复用
    echo=False,
    connect_args={
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000",  # 30秒超时
    },
)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Session context manager"""
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def register_after_commit(session, callback) -> None:
    if not hasattr(session, "info"):
        callback()
        return
    session.info.setdefault(AFTER_COMMIT_CALLBACKS_KEY, []).append(callback)


@event.listens_for(Session, "after_commit")
def _run_after_commit_callbacks(session: Session) -> None:
    callbacks = session.info.pop(AFTER_COMMIT_CALLBACKS_KEY, [])
    for callback in callbacks:
        callback()


@event.listens_for(Session, "after_rollback")
def _clear_after_commit_callbacks(session: Session) -> None:
    session.info.pop(AFTER_COMMIT_CALLBACKS_KEY, None)


# FastAPI dependency
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions"""
    with get_session() as session:
        yield session
