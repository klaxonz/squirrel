import logging
import os
import uvicorn
from alembic.config import Config as AlembicConfig
from alembic import command
from common.constants import SYS_ENABLE_SCHEDULER, SYS_ENABLE_WORKER
from common.global_config import IS_DEV
from common.log import init_logging
from controllers.scheduler_controller import scheduler_start, scheduler_stop
from controllers.worker_controller import worker_start, worker_stop
from routes.base import app
from services.system_config_service import get_bool
from plugins.loader import app_stop

logger = logging.getLogger()


def upgrade_database():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    alembic_ini_path = os.path.join(current_dir, "alembic.ini")
    logger.info(f"Upgrading database with alembic.ini: {alembic_ini_path}")
    alembic_cfg = AlembicConfig(alembic_ini_path)
    command.upgrade(alembic_cfg, "head")


def start_fastapi_server():
    if IS_DEV:
        uvicorn.run("main:app", host="0.0.0.0", reload=True, port=8000)
    else:
        uvicorn.run(app, host="0.0.0.0", port=8000)


def main():
    upgrade_database()
    init_logging()
    enable_worker = get_bool(SYS_ENABLE_WORKER, True)
    enable_scheduler = get_bool(SYS_ENABLE_SCHEDULER, True)
    if enable_worker:
        worker_start()
    else:
        logger.info("Worker disabled by system config")

    if enable_scheduler:
        scheduler_start()
    else:
        logger.info("Scheduler disabled by system config")

    logger.info('Starting server...')
    try:
        start_fastapi_server()
    finally:
        # graceful stop
        try:
            scheduler_stop()
        except Exception:
            logger.exception("Error when stopping scheduler (ignored)")
        try:
            app_stop()
        except Exception:
            logger.exception("Error when stopping plugins (ignored)")
        try:
            worker_stop()
        except Exception:
            logger.exception("Error when stopping workers (ignored)")


if __name__ == "__main__":
    main()
