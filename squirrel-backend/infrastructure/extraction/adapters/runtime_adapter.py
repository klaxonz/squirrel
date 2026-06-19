"""Plugin data adapter - converts plugin Video objects to VideoDTO

Core improvements:
1. Actively fetches all required data (including lazy-loaded actors)
2. Catches all exceptions and standardizes them
3. Returns pure data objects (VideoDTO)
"""

import logging
from datetime import datetime
from typing import Any

from ..dto.actor_dto import ActorDTO
from ..dto.validators import parse_publish_date
from ..dto.video_dto import VideoDTO
from ..exceptions import DataTransformError
from ..runtime_payloads import RuntimeActorData, RuntimeVideoData

logger = logging.getLogger(__name__)


class RuntimeDataAdapter:
    """Plugin data adapter

    Responsibilities:
    - Converts plugin Video objects to VideoDTO
    - Actively triggers lazy-loaded properties (e.g. actors)
    - Unifies data format
    - Error handling and logging
    """

    def __init__(self):
        self.logger = logger

    def adapt(self, video: RuntimeVideoData, site_name: str) -> VideoDTO:
        """Convert plugin Video object to VideoDTO

        Args:
            video: Video object returned by the plugin
            site_name: Site name

        Returns:
            VideoDTO object

        Raises:
            DataTransformError: Conversion failed

        """
        try:
            # 1. Extract base fields
            base_data = self._extract_base_fields(video, site_name)

            # 2. Handle publish date
            publish_date = self._extract_publish_date(video)
            if publish_date:
                base_data['publish_date'] = publish_date

            # 3. Actively fetch actors (critical!)
            actors = self._extract_actors(video)
            if actors:
                base_data['actors'] = actors

            # 4. Preserve raw data
            base_data['raw_data'] = self._extract_raw_data(video)

            # 5. Create DTO (with automatic validation)
            video_dto = VideoDTO(**base_data)

            self.logger.debug(
                'Video adapted successfully: %s',
                video.url,
                extra={'url': video.url, 'site': site_name, 'actors_count': len(actors)},
            )

            return video_dto

        except Exception as e:  # data transform boundary — wrap any error as DataTransformError
            self.logger.error(
                'Failed to adapt Video to VideoDTO: %s',
                getattr(video, 'url', 'unknown'),
                exc_info=True,
                extra={
                    'url': getattr(video, 'url', None),
                    'site': site_name,
                    'error': str(e),
                    'error_type': type(e).__name__,
                },
            )

            raise DataTransformError(
                f'Failed to transform video data: {e}',
                context={
                    'url': getattr(video, 'url', None),
                    'site': site_name,
                    'original_error': str(e),
                },
            ) from e

    def _extract_base_fields(self, video: RuntimeVideoData, site_name: str) -> dict[str, Any]:
        """Extract base fields

        Args:
            video: VideoMeta object
            site_name: Site name

        Returns:
            Dictionary of base fields

        """
        # VideoMeta base fields
        base_data = {
            'url': video.url,
            'title': video.title or '',
            'site_name': site_name,
        }

        # Optional fields
        if video.thumbnail is not None:
            base_data['thumbnail'] = video.thumbnail

        if video.duration is not None:
            base_data['duration'] = video.duration

        # Extract additional fields from extra_data (e.g. description, tags)
        if video.extra_data:
            if 'description' in video.extra_data:
                base_data['description'] = video.extra_data['description']
            if 'tags' in video.extra_data:
                base_data['tags'] = video.extra_data['tags']

        return base_data

    def _extract_publish_date(self, video: RuntimeVideoData) -> datetime | None:
        """Extract publish date (supports multiple formats)

        Args:
            video: VideoMeta object

        Returns:
            datetime object or None

        """
        # VideoMeta publish_date field
        if video.publish_date is not None:
            return parse_publish_date(video.publish_date)

        return None

    def _extract_actors(self, video: RuntimeVideoData) -> list[ActorDTO]:
        """Extract actor information

        Actors in VideoMeta may be stored in extra_data

        Args:
            video: VideoMeta object

        Returns:
            List of ActorDTO

        """
        actors = []

        try:
            # Get actors from extra_data
            if video.extra_data and 'actors' in video.extra_data:
                raw_actors = video.extra_data['actors']

                if raw_actors and isinstance(raw_actors, list):
                    for actor in raw_actors:
                        try:
                            # Convert dictionary payloads to backend-local actor data.
                            if isinstance(actor, dict):
                                actor = RuntimeActorData(
                                    url=actor.get('url', ''),
                                    name=actor.get('name'),
                                    avatar=actor.get('avatar'),
                                    extra_data=actor.get('extra_data'),
                                )

                            actor_dto = self._convert_actor(actor)
                            if actor_dto:
                                actors.append(actor_dto)
                        except (ValueError, TypeError, AttributeError, KeyError) as e:
                            self.logger.warning(
                                'Failed to convert actor: %s', e, extra={'video_url': video.url, 'actor': str(actor)}
                            )

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            # Actor extraction failure should not abort the entire extraction
            self.logger.warning(
                'Failed to extract actors: %s, error: %s', video.url, e, extra={'url': video.url, 'error': str(e)}
            )

        return actors

    def _convert_actor(self, actor: RuntimeActorData) -> ActorDTO | None:
        """Convert a single Actor object to ActorDTO

        Args:
            actor: Actor object

        Returns:
            ActorDTO or None

        """
        if not isinstance(actor, RuntimeActorData):
            return None

        # Ensure url and name are present
        if not hasattr(actor, 'url') or not actor.url:
            return None

        if not hasattr(actor, 'name') or not actor.name:
            return None

        return ActorDTO(
            url=actor.url,
            name=actor.name,
            avatar=getattr(actor, 'avatar', None),
        )

    def _extract_raw_data(self, video: RuntimeVideoData) -> dict[str, Any]:
        """Extract raw data (for debugging and auditing)

        Args:
            video: VideoMeta object

        Returns:
            Raw data dictionary

        """
        raw = {}

        # Save extra_data if present
        if video.extra_data:
            # Only save serializable data
            raw['extra_data'] = {
                k: v
                for k, v in video.extra_data.items()
                if isinstance(v, (str, int, float, bool, type(None), list, dict))
            }

        return raw
