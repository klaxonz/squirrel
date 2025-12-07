"""
Data Transfer Objects for extraction pipeline.

提供纯数据对象，用于在各个组件之间传递数据。
"""

from .actor_dto import ActorDTO
from .video_dto import VideoDTO
from .validators import (
    validate_url,
    validate_not_empty,
    parse_publish_date,
)

__all__ = [
    'ActorDTO',
    'VideoDTO',
    'validate_url',
    'validate_not_empty',
    'parse_publish_date',
]
