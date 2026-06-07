"""Data Transfer Objects for extraction pipeline.

Provides pure data objects for transferring data between components.
"""

from .actor_dto import ActorDTO
from .validators import (
    parse_publish_date,
    validate_not_empty,
    validate_url,
)
from .video_dto import VideoDTO

__all__ = [
    "ActorDTO",
    "VideoDTO",
    "parse_publish_date",
    "validate_not_empty",
    "validate_url",
]
