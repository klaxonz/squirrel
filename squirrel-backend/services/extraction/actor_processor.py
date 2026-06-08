"""Actor processing service - handles actor/creator data
"""
import logging

from core.extraction.dto import ActorDTO
from services import creator_service, video_creator_service

logger = logging.getLogger(__name__)


class ActorProcessorService:
    """Actor processing service

    Responsibilities:
    - Create or retrieve actor records
    - Create video-actor associations
    """

    def process_actors(self, video_id: int, actors: list[ActorDTO]):
        """Process actor list

        Args:
            video_id: Video ID
            actors: List of actor DTOs

        """
        if not actors:
            return

        logger.debug("Processing %s actors for video_id=%s", len(actors), video_id)

        for actor_dto in actors:
            try:
                self._process_single_actor(video_id, actor_dto)
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning("Failed to process actor: video_id=%s, actor_url=%s, error=%s", video_id, actor_dto.url, e)
                # Continue processing other actors

    def _process_single_actor(self, video_id: int, actor_dto: ActorDTO):
        """Process a single actor"""
        # 1. Get or create creator
        creator = creator_service.get_creator_by_url(actor_dto.url)

        if not creator:
            creator = creator_service.create_creator(
                actor_dto.url,
                actor_dto.name,
                actor_dto.avatar,
            )
            logger.debug("Created new creator: id=%s, name=%s", creator.id, actor_dto.name)

        # 2. Create video-creator association
        video_creator = video_creator_service.get_video_creator(
            video_id, creator.id,
        )

        if not video_creator:
            video_creator_service.create_video_creator(
                video_id, creator.id,
            )
            logger.debug("Created video-creator link: video_id=%s, creator_id=%s", video_id, creator.id)


# Singleton instance
actor_processor_service = ActorProcessorService()
