import logging
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from domains.subscription.application.services.core.sync.state._ownership import has_live_execution_token
from domains.subscription.application.services.crawl.tasks import service as crawl_task_service_module
from domains.subscription.application.services.crawl.tasks.errors import CrawlTaskStateError
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState
from domains.video.application.services.crud import VideoCrudService
from domains.video.interfaces.dto.video_dto import VideoExtractDto
from infrastructure.database.session import get_session
from infrastructure.site_catalog.catalog import SiteCatalog
from infrastructure.site_catalog.url import extract_top_level_domain

logger = logging.getLogger(__name__)


class VideoExtractionTaskService:
    def __init__(
        self,
        get_video_by_url=None,
        crawl_tasks=None,
        *,
        reserve_sync_progress: bool = True,
        session_factory=None,
    ):
        self._session_factory = session_factory or get_session
        self._get_video_by_url = get_video_by_url or VideoCrudService(
            session_factory=self._session_factory,
        ).get_video_by_url
        self._crawl_tasks = crawl_tasks or crawl_task_service_module.crawl_task_service
        self._reserve_sync_progress = reserve_sync_progress

    def enqueue(self, params: VideoExtractDto) -> bool:
        domain = extract_top_level_domain(params.url)
        if not SiteCatalog.is_site_enabled(domain=domain):
            logger.info('Skip enqueue video extraction for disabled site: domain=%s, url=%s', domain, params.url)
            return False

        if params.only_extract:
            video = self._get_video_by_url(params.url)
            if video:
                logger.debug('Video already extracted, skipping: %s', params.url)
                return False

        return self._create_task(params)

    @staticmethod
    def build_dedupe_key(
        url: str,
        subscription_id: int | None = None,
        run_id: str | None = None,
    ) -> str:
        subscription_scope = str(subscription_id) if subscription_id else 'global'
        run_scope = str(run_id) if run_id else 'standalone'
        return f'dedupe:video_extract:{subscription_scope}:{run_scope}:{sha256(url.strip().encode()).hexdigest()}'

    def _create_task(self, params: VideoExtractDto) -> bool:
        if self._reserve_sync_progress and params.sync_state_id and not params.run_id:
            raise CrawlTaskStateError(
                f'Video extraction for sync_state_id={params.sync_state_id} is missing run_id fencing',
            )
        content = params.model_dump()
        if params.is_manual:
            priority = 'manual'
        elif params.is_extract_all:
            priority = 'full'
        else:
            priority = 'incr'

        domain = extract_top_level_domain(params.url)
        is_standalone_manual = params.is_manual and not (params.sync_state_id and params.run_id)
        dedupe_key = (
            None
            if is_standalone_manual
            else self.build_dedupe_key(params.url, params.subscription_id, params.run_id)
        )
        source_type = 'manual' if params.is_manual else 'scheduled'

        try:
            with self._crawl_tasks.session_factory() as session:
                sync_state = None
                if params.sync_state_id and params.run_id and self._reserve_sync_progress:
                    sync_state = session.execute(
                        select(SubscriptionSyncState)
                        .where(SubscriptionSyncState.id == params.sync_state_id)
                        .with_for_update(),
                    ).scalar_one_or_none()
                    if (
                        sync_state is None
                        or sync_state.current_run_id != params.run_id
                        or not has_live_execution_token(
                            session,
                            sync_state,
                            params.parent_execution_token,
                        )
                    ):
                        raise CrawlTaskStateError(
                            f'Stale video extraction parent: sync_state_id={params.sync_state_id}, '
                            f'run_id={params.run_id}',
                        )

                _, _task = self._crawl_tasks.create_job_with_task_in_session(
                    session,
                    job_type='video_extract',
                    source_type=source_type,
                    site=domain,
                    subscription_id=params.subscription_id,
                    priority=priority,
                    task_type='video_extract',
                    payload=content,
                    dedupe_key=dedupe_key,
                    sync_state_id=params.sync_state_id,
                    run_id=params.run_id,
                    video_url=params.url,
                    trace_id=params.run_id,
                )
                if sync_state is not None:
                    sync_state.pending_video_count += 1
                    sync_state.version += 1
            return True
        except IntegrityError as exc:
            constraint_name = getattr(getattr(exc.orig, 'diag', None), 'constraint_name', None)
            if (
                constraint_name not in {None, 'uq_crawl_task_dedupe_key'}
                or not dedupe_key
                or not self._crawl_tasks.has_task_with_dedupe_key(dedupe_key)
            ):
                raise
            logger.debug('Video extraction task already exists in task store, skipping: %s', params.url)
            return False
