import logging
import os

from alembic import command
from alembic.config import Config as AlembicConfig

logger = logging.getLogger(__name__)


def upgrade_database() -> None:
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_ini_path = os.path.join(current_dir, "alembic.ini")
    alembic_script_path = os.path.join(current_dir, "alembic")
    logger.info("Upgrading database with alembic.ini: %s", alembic_ini_path)
    alembic_cfg = AlembicConfig(alembic_ini_path)
    alembic_cfg.set_main_option("script_location", alembic_script_path)
    alembic_cfg.set_main_option("prepend_sys_path", current_dir)
    alembic_cfg.attributes["skip_logging_config"] = True
    command.upgrade(alembic_cfg, "head")
