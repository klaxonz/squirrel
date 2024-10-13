import logging

from core.config import settings
from sqlmodel import create_engine, Session

logger = logging.getLogger(__name__)

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


def get_session() -> Session:
    s = Session(engine)
    try:
        yield s
        s.commit()
    except Exception as e:
        s.rollback()
        raise e
    finally:
        s.close()
