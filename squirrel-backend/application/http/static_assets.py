import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


def mount_static_assets(application: FastAPI) -> None:
    mount_static(application, '/static/thumbnails', settings.thumbnails_dir, 'thumbnails')
    mount_static(application, '/static/clip-markers', settings.clip_marker_previews_dir, 'clip-marker-previews')


def mount_static(application: FastAPI, path: str, directory: Path, name: str) -> None:
    """Mount an optional static directory when it exists."""
    if not directory.exists():
        logger.warning('Static directory not found: %s, skipping %s mounting', directory, name)
        return
    application.mount(path, StaticFiles(directory=directory), name=name)
    logger.info('%s mounted: %s', name, directory)
