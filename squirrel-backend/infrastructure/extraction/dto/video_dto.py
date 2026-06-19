"""VideoDTO - Video data transfer object"""

from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel, Field, validator

from .actor_dto import ActorDTO
from .validators import (
    parse_publish_date,
    validate_duration,
    validate_not_empty,
    validate_url,
)


class VideoDTO(BaseModel):
    """Video data transfer object

    Features:
    - Pure data object, no behavior
    - Immutable (frozen=True)
    - Automatic field validation
    - Serializable, cacheable
    - Unified data format

    Difference from plugin Video object:
    - Video object: lazy-loaded attributes, may trigger HTTP requests
    - VideoDTO: pure data, all fields immediately available, no side effects
    """

    # ========== Required fields ==========
    url: str = Field(..., description='Video URL')
    title: str = Field(..., description='Video title')
    site_name: str = Field(..., description='Site name, e.g. bilibili, youtube')

    # ========== Optional basic fields ==========
    thumbnail: str | None = Field(None, description='Thumbnail URL')
    duration: int | None = Field(None, ge=0, description='Video duration in seconds')
    publish_date: datetime | None = Field(None, description='Publish date')
    description: str | None = Field(None, description='Video description')
    tags: list[str] | None = Field(None, description='Tag list')

    # ========== Related data ==========
    actors: list[ActorDTO] = Field(default_factory=list, description='Actor/Creator list')

    # ========== Metadata ==========
    raw_data: dict[str, Any] | None = Field(
        None,
        description='Raw data (for debugging and auditing)',
    )

    class Config:
        frozen = True  # Immutable object
        json_encoders: ClassVar[dict[type[datetime], Any]] = {
            datetime: lambda v: v.isoformat() if v else None,
        }

    # ========== Validators ==========

    @validator('url')
    def validate_url_field(cls, v):
        """Validate URL format"""
        return validate_url(v)

    @validator('title')
    def validate_title(cls, v):
        """Validate title is not empty"""
        return validate_not_empty(v, 'Title')

    @validator('site_name')
    def validate_site_name(cls, v):
        """Validate site name"""
        return validate_not_empty(v, 'Site name')

    @validator('thumbnail')
    def validate_thumbnail_url(cls, v):
        """Validate thumbnail URL (optional)"""
        if v is None or v == '':
            return None

        v = v.strip()

        if not v:
            return None

        # Thumbnail URL can be a relative path or absolute URL
        if v.startswith(('http://', 'https://', '/')):
            return v

        raise ValueError('Thumbnail URL must be absolute or relative path')

    @validator('duration')
    def validate_duration_field(cls, v):
        """Validate duration"""
        return validate_duration(v)

    @validator('publish_date', pre=True)
    def parse_and_validate_publish_date(cls, v):
        """Parse and validate publish date"""
        return parse_publish_date(v)

    @validator('description')
    def clean_description(cls, v):
        """Clean description text"""
        if v is None or v == '':
            return None

        # Strip leading/trailing whitespace
        v = v.strip()

        if not v:
            return None

        # Limit length to avoid overly long descriptions
        max_length = 10000
        if len(v) > max_length:
            v = v[:max_length] + '...'

        return v

    @validator('tags')
    def validate_tags(cls, v):
        """Validate tag list"""
        if v is None or v == []:
            return None

        if not isinstance(v, list):
            raise ValueError('Tags must be a list')

        # Clean tags
        cleaned_tags = []
        for tag in v:
            if isinstance(tag, str):
                tag = tag.strip()
                if tag:
                    cleaned_tags.append(tag)

        return cleaned_tags or None

    @validator('actors')
    def validate_actors_list(cls, v):
        """Validate actor list"""
        if v is None:
            return []

        if not isinstance(v, list):
            raise ValueError('Actors must be a list')

        # Ensure all elements are ActorDTO instances
        for actor in v:
            if not isinstance(actor, ActorDTO):
                raise ValueError(f'Actor must be ActorDTO instance, got {type(actor)}')

        return v

    # ========== Utility methods ==========

    def to_dict(self, exclude_none: bool = True) -> dict[str, Any]:
        """Convert to dictionary

        Args:
            exclude_none: Whether to exclude None values

        Returns:
            Dictionary representation

        """
        data = self.dict(exclude_none=exclude_none)

        # Convert actors to list of dicts
        if data.get('actors'):
            data['actors'] = [actor.to_dict() for actor in self.actors]

        # Convert datetime to ISO format string
        if data.get('publish_date'):
            data['publish_date'] = self.publish_date.isoformat()

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'VideoDTO':
        """Create from dictionary

        Args:
            data: Dictionary data

        Returns:
            VideoDTO instance

        """
        # Convert actors
        if data.get('actors') and isinstance(data['actors'], list):
            data['actors'] = [ActorDTO(**actor) if isinstance(actor, dict) else actor for actor in data['actors']]

        return cls(**data)

    def has_actors(self) -> bool:
        """Whether actor information is available"""
        return bool(self.actors)

    def has_thumbnail(self) -> bool:
        """Whether thumbnail is available"""
        return bool(self.thumbnail)

    def has_publish_date(self) -> bool:
        """Whether publish date is available"""
        return self.publish_date is not None

    def get_summary(self) -> str:
        """Get summary string (for logging)"""
        return (
            f"VideoDTO(url='{self.url}', title='{self.title[:50]}...', "
            f"site='{self.site_name}', actors={len(self.actors)})"
        )

    def __repr__(self):
        return self.get_summary()
