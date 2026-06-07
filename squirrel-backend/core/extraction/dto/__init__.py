"""Data Transfer Objects for extraction pipeline.

提供纯数据对象，用于在各个组件之间传递数据。
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
