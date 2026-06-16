import logging

import uvicorn
from fastapi import FastAPI

from application.lifespan import lifespan
from infrastructure.config.settings import settings
from infrastructure.database.migrations import upgrade_database
from shared_kernel.infrastructure.log import init_logging

logger = logging.getLogger(__name__)


def create_application() -> FastAPI:
    """Create a FastAPI application instance with lifecycle management."""
    from application.app import create_app

    app = create_app()
    app.router.lifespan_context = lifespan
    return app


def main() -> None:
    """Application main entry point."""
    upgrade_database()
    init_logging()

    logger.info(
        "Launching FastAPI server host=%s port=%s mode=%s",
        "0.0.0.0",
        settings.PORT,
        "development" if settings.is_dev else "production",
    )

    if settings.is_dev:
        uvicorn.run(
            "main:create_application",
            host="0.0.0.0",
            port=settings.PORT,
            reload=False,
            factory=True,
            log_config=None,
            access_log=False,
        )
    else:
        app = create_application()
        uvicorn.run(app, host="0.0.0.0", port=settings.PORT, log_config=None, access_log=False)


if __name__ == "__main__":
    main()
