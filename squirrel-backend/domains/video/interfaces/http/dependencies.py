"""FastAPI dependency providers for the video HTTP layer.

These give every request its own service instance wired to the request-scoped
session, instead of routes grabbing a process-wide module singleton. The
services themselves already accept an injectable ``session_factory`` -- this
just exposes that capability to the routing layer.
"""

from domains.video.application.services.crud import VideoCrudService
from domains.video.application.services.listing.service import VideoListService
from domains.video.application.services.random import VideoRandomService


def get_video_crud_service() -> VideoCrudService:
    """Per-request ``VideoCrudService`` (create/save)."""
    return VideoCrudService()


def get_video_list_service() -> VideoListService:
    """Per-request ``VideoListService`` (list/detail)."""
    return VideoListService()


def get_video_random_service() -> VideoRandomService:
    """Per-request ``VideoRandomService`` (random video)."""
    return VideoRandomService()
