import contextlib
import datetime

from sqlalchemy import create_engine, Column, DateTime, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from common.config import GlobalConfig
import logging

logger = logging.getLogger(__name__)

db_config = {
    'host': GlobalConfig.get_mysql_host(),
    'port': GlobalConfig.get_mysql_port(),
    'user': GlobalConfig.get_mysql_user(),
    'password': GlobalConfig.get_mysql_password(),
    'database': GlobalConfig.get_mysql_database(),
}

engine = create_engine(
    GlobalConfig.get_mysql_url(),
    pool_size=GlobalConfig.POOL_SIZE,
    max_overflow=GlobalConfig.POOL_MAX_SIZE,
    pool_recycle=GlobalConfig.POOL_RECYCLE,
    connect_args={"init_command": "SET time_zone='+08:00'"}
)
Session = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()


class BaseMixin:
    """model的基类,所有model都必须继承"""
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now,
                        index=True)


@event.listens_for(engine, "before_cursor_execute")
def comment_sql_calls(conn, cursor, statement, parameters, context, executemany):
    raw_sql = statement % parameters
    logger.debug(f"执行SQL: {raw_sql}")


@contextlib.contextmanager
def get_session() -> Session:
    s = Session()
    try:
        yield s
        s.commit()
    except Exception as e:
        s.rollback()
        raise e
    finally:
        s.close()
