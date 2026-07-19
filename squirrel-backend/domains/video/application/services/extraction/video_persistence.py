"""Video persistence service - handles video database operations"""

import logging
from collections.abc import Callable, Generator
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import infrastructure.site_catalog.url as url_helper
from domains.subscription.application.services.core.sync.state._ownership import (
    has_live_execution_token,
    has_live_video_task_token,
)
from domains.subscription.application.services.crawl.tasks.errors import CrawlTaskStateError
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.video.domain.junctions.video_creator import VideoCreator
from domains.video.domain.models.creator import Creator
from domains.video.domain.models.video import Video as VideoModel
from infrastructure.config.settings import settings
from infrastructure.database.session import get_session as _default_get_session
from infrastructure.database.session import register_after_commit
from infrastructure.extraction.dto.actor_dto import ActorDTO
from shared_kernel.domain.events import DomainEvents, domain_events

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Generator[Session, None, None]]


def _index_video_after_commit(session: Session, video: VideoModel) -> None:
    """事务提交后把 video 推到 Meilisearch(增量直写,失败仅告警)。

    发布 ``video.saved`` 事件,由在 bootstrap 注册的 Meilisearch 监听器消费,
    本模块不再直接依赖 meili_indexer,从而消除函数内 import。
    """
    if not settings.meili.url:
        return
    try:
        register_after_commit(session, lambda: domain_events.fire(DomainEvents.VIDEO_SAVED, {'video_id': video.id}))
    except Exception:
        logger.warning('meili index register failed video_id=%s', getattr(video, 'id', None), exc_info=True)


class VideoPersistenceService:
    """Video persistence service

    Responsibilities:
    - Create or update video records
    - Create subscription-video associations
    - Update subscription statistics
    """

    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session

    def create_or_update(
        self,
        *,
        url: str,
        title: str,
        thumbnail: str | None = None,
        duration: int | None = None,
        publish_date: datetime | None = None,
        description: str | None = None,
        subscription_id: int | None = None,
        subscription_sync_mode: str | None = None,
        sync_state_id: int | None = None,
        run_id: str | None = None,
        execution_token: str | None = None,
        crawl_task_id: int | None = None,
        actors: list[ActorDTO] | None = None,
    ) -> tuple[VideoModel, bool]:
        with self._session_factory() as session:
            self._assert_sync_write_owned(
                session,
                sync_state_id=sync_state_id,
                run_id=run_id,
                execution_token=execution_token,
                crawl_task_id=crawl_task_id,
            )
            video, is_new = self._create_or_update_in_session(
                session,
                url=url,
                title=title,
                thumbnail=thumbnail,
                duration=duration,
                publish_date=publish_date,
                description=description,
                subscription_id=subscription_id,
                subscription_sync_mode=subscription_sync_mode,
            )
            self.process_actors_in_session(session, video.id, actors or [])
            session.flush()
            return video, is_new

    def link_existing_videos(
        self,
        subscription_id: int,
        video_ids: list[int],
        *,
        sync_state_id: int | None = None,
        run_id: str | None = None,
        execution_token: str | None = None,
    ) -> int:
        """Idempotently attach already-extracted videos to another subscription."""
        unique_ids = list(dict.fromkeys(int(video_id) for video_id in video_ids if video_id))
        if not subscription_id or not unique_ids:
            return 0

        created = 0
        with self._session_factory() as session:
            self._assert_sync_write_owned(
                session,
                sync_state_id=sync_state_id,
                run_id=run_id,
                execution_token=execution_token,
                crawl_task_id=None,
            )
            linked_ids = set(
                session.scalars(
                    select(SubscriptionVideo.video_id).where(
                        SubscriptionVideo.subscription_id == subscription_id,
                        SubscriptionVideo.video_id.in_(unique_ids),
                    ),
                ).all(),
            )
            for video_id in unique_ids:
                if video_id in linked_ids:
                    continue
                savepoint = session.begin_nested()
                try:
                    session.add(SubscriptionVideo(subscription_id=subscription_id, video_id=video_id))
                    session.flush()
                except IntegrityError:
                    savepoint.rollback()
                    continue
                savepoint.commit()
                _index_video_id_after_commit(session, video_id)
                created += 1
        return created

    @staticmethod
    def _assert_sync_write_owned(
        session: Session,
        *,
        sync_state_id: int | None,
        run_id: str | None,
        execution_token: str | None,
        crawl_task_id: int | None,
    ) -> None:
        if sync_state_id is None and run_id is None and execution_token is None and crawl_task_id is None:
            return
        if sync_state_id is None or run_id is None or execution_token is None:
            raise CrawlTaskStateError('Run-bound video persistence is missing its fencing identity')

        state = session.execute(
            select(SubscriptionSyncState)
            .where(SubscriptionSyncState.id == sync_state_id)
            .with_for_update(),
        ).scalar_one_or_none()
        if state is None or state.current_run_id != run_id:
            raise CrawlTaskStateError(
                f'Stale video persistence run: sync_state_id={sync_state_id}, run_id={run_id}',
            )

        owned = (
            has_live_video_task_token(
                session,
                state,
                run_id=run_id,
                execution_token=execution_token,
                task_id=crawl_task_id,
            )
            if crawl_task_id is not None
            else has_live_execution_token(session, state, execution_token)
        )
        if not owned:
            raise CrawlTaskStateError(
                f'Stale video persistence execution: sync_state_id={sync_state_id}, run_id={run_id}',
            )
        if crawl_task_id is None and execution_token.startswith('direct:'):
            state.locked_at = datetime.now()

    def _create_subscription_link(
        self,
        session: Session,
        subscription_id: int,
        video_id: int,
        is_new_video: bool,
        *,
        subscription_sync_mode: str | None,
    ) -> None:
        existing = session.get(
            SubscriptionVideo,
            {
                'subscription_id': subscription_id,
                'video_id': video_id,
            },
        )
        if existing:
            return

        session.add(SubscriptionVideo(subscription_id=subscription_id, video_id=video_id))
        _index_video_id_after_commit(session, video_id)
        logger.debug(
            'Created subscription-video link: subscription_id=%s, video_id=%s, is_new_video=%s, sync_mode=%s',
            subscription_id,
            video_id,
            is_new_video,
            subscription_sync_mode,
        )

    def process_actors_in_session(self, session: Session, video_id: int, actors: list[ActorDTO]) -> None:
        if not actors:
            return

        logger.debug('Processing %s actors for video_id=%s', len(actors), video_id)
        for actor_dto in actors:
            creator = session.scalars(select(Creator).where(Creator.url == actor_dto.url)).first()
            if creator is None:
                creator = Creator(
                    url=actor_dto.url,
                    name=actor_dto.name,
                    avatar=actor_dto.avatar,
                    description=None,
                    extra_data={},
                )
                session.add(creator)
                session.flush()
                logger.debug('Created new creator: id=%s, name=%s', creator.id, actor_dto.name)

            existing_link = session.get(
                VideoCreator,
                {
                    'video_id': video_id,
                    'creator_id': creator.id,
                },
            )
            if existing_link is None:
                session.add(VideoCreator(video_id=video_id, creator_id=creator.id))
                _index_video_id_after_commit(session, video_id)
                logger.debug('Created video-creator link: video_id=%s, creator_id=%s', video_id, creator.id)

    def _create_or_update_in_session(
        self,
        session: Session,
        *,
        url: str,
        title: str,
        thumbnail: str | None = None,
        duration: int | None = None,
        publish_date: datetime | None = None,
        description: str | None = None,
        subscription_id: int | None = None,
        subscription_sync_mode: str | None = None,
    ) -> tuple[VideoModel, bool]:
        video = session.scalars(select(VideoModel).where(VideoModel.url == url)).first()
        is_new = video is None

        if is_new:
            if publish_date is None:
                logger.warning('Missing publish_date when creating video: url=%s', url)
            video = VideoModel(
                url=url,
                domain=url_helper.normalize_domain(url),
                title=title,
                thumbnail=thumbnail,
                duration=duration,
                publish_date=publish_date,
                description=description,
            )
            session.add(video)
            session.flush()
            _index_video_after_commit(session, video)
            logger.info('Created new video: id=%s, url=%s', video.id, url)
        else:
            updated = False
            normalized_domain = url_helper.normalize_domain(url)
            if normalized_domain and normalized_domain != video.domain:
                video.domain = normalized_domain
                updated = True
            if title and title != video.title:
                video.title = title
                updated = True
            if thumbnail is not None and thumbnail != video.thumbnail:
                video.thumbnail = thumbnail
                updated = True
            if duration is not None and duration != video.duration:
                video.duration = duration
                updated = True
            if publish_date is not None and publish_date != video.publish_date:
                video.publish_date = publish_date
                updated = True
            if description is not None and description != video.description:
                video.description = description
                updated = True
            if updated:
                _index_video_after_commit(session, video)
                logger.info('Updated video: id=%s, url=%s', video.id, url)
            else:
                logger.debug('Video already exists: id=%s, url=%s', video.id, url)

        if subscription_id:
            self._create_subscription_link(
                session,
                subscription_id,
                video.id,
                is_new,
                subscription_sync_mode=subscription_sync_mode,
            )

        return video, is_new


# Singleton instance
video_persistence_service = VideoPersistenceService()


def _index_video_id_after_commit(session: Session, video_id: int) -> None:
    if not settings.meili.url:
        return
    register_after_commit(session, lambda: domain_events.fire(DomainEvents.VIDEO_SAVED, {'video_id': video_id}))
