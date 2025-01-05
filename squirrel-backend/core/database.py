import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from common.log import init_logging
from core.config import settings

init_logging()
logger = logging.getLogger()

db_config = {
    'host': settings.MYSQL_HOST,
    'port': settings.MYSQL_PORT,
    'user': settings.MYSQL_USER,
    'password': settings.MYSQL_PASSWORD,
    'database': settings.MYSQL_DATABASE,
}

engine = create_engine(
    settings.database_url,
    pool_size=settings.POOL_SIZE,
    max_overflow=settings.POOL_MAX_SIZE,
    pool_recycle=settings.POOL_RECYCLE,
    connect_args={"init_command": "SET time_zone='+08:00'"}
)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Session context manager"""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# FastAPI dependency
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions"""
    with get_session() as session:
        yield session
