import logging
import os
from contextlib import contextmanager

from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from alembic import command
from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

_MIGRATION_LOCK_ID = 7350438400214821


@contextmanager
def _migration_lock():
    engine = create_engine(settings.database_url, poolclass=NullPool)
    with engine.connect() as connection:
        connection.execute(text('SELECT pg_advisory_lock(:lock_id)'), {'lock_id': _MIGRATION_LOCK_ID})
        try:
            yield
        finally:
            connection.execute(text('SELECT pg_advisory_unlock(:lock_id)'), {'lock_id': _MIGRATION_LOCK_ID})
            engine.dispose()


def upgrade_database() -> None:
    # Get the squirrel-backend root directory (3 levels up from this file)
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    alembic_ini_path = os.path.join(current_dir, 'alembic.ini')
    alembic_script_path = os.path.join(current_dir, 'alembic')
    logger.info('Upgrading database with alembic.ini: %s', alembic_ini_path)
    alembic_cfg = AlembicConfig(alembic_ini_path)
    alembic_cfg.set_main_option('script_location', alembic_script_path)
    alembic_cfg.set_main_option('prepend_sys_path', current_dir)
    alembic_cfg.attributes['skip_logging_config'] = True
    with _migration_lock():
        command.upgrade(alembic_cfg, 'head')
