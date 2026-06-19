"""PersistenceStage - persists video data to database"""

import logging

from ...exceptions import DatabaseError
from ..base import PipelineStage
from ..context import PipelineContext

logger = logging.getLogger(__name__)


class PersistenceStage(PipelineStage):
    """Persistence stage

    Responsibilities:
    - Save video to database
    - Create subscription-video association
    - Process actor information
    - Save to context.video_model
    """

    def __init__(self, video_service, actor_service):
        """Args:
        video_service: Video persistence service
        actor_service: Actor processing service

        """
        self.video_service = video_service
        self.actor_service = actor_service

    @property
    def stage_name(self) -> str:
        return 'persistence'

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute persistence"""
        # Check preconditions
        if context.video_dto is None:
            raise DatabaseError(
                'No video DTO found in context',
                context={'task_id': context.task.task_id},
            )

        # Check if persistence should be skipped
        if context.should_skip_persistence:
            logger.info('Skipping persistence (flag set): url=%s', context.task.url)
            return context

        dto = context.video_dto
        task = context.task

        # 1. Save video
        logger.info('Persisting video: url=%s, title=%s', dto.url, dto.title)

        try:
            video_model, is_new = self.video_service.create_or_update(
                url=dto.url,
                title=dto.title,
                thumbnail=dto.thumbnail,
                duration=dto.duration,
                publish_date=dto.publish_date,
                description=dto.description,
                subscription_id=task.metadata.get('subscription_id'),
                subscription_sync_mode=task.metadata.get('sync_mode'),
            )

            context.video_model = video_model
            context.extra['is_new_video'] = is_new

            logger.info('Video persisted: id=%s, is_new=%s, url=%s', video_model.id, is_new, dto.url)

        except (ConnectionError, OSError, ValueError, TypeError) as e:
            raise DatabaseError(
                f'Failed to persist video: {e}',
                context={
                    'url': dto.url,
                    'title': dto.title,
                },
            ) from e

        # 2. Process actors
        if dto.has_actors():
            try:
                self.actor_service.process_actors(
                    video_model.id,
                    dto.actors,
                )
                logger.info('Actors processed: video_id=%s, count=%s', video_model.id, len(dto.actors))
            except (ValueError, TypeError, AttributeError) as e:
                # Actor processing failure should not interrupt the flow
                logger.warning('Failed to process actors: video_id=%s, error=%s', video_model.id, e)

        return context

    def can_skip(self, context: PipelineContext) -> bool:
        """Skip if video_model already exists or skip flag is set"""
        return context.video_model is not None or context.should_skip_persistence
