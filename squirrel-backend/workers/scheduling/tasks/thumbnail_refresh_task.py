import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import func, select

from domains.video.application.services.extraction.thumbnail_downloader import ThumbnailDownloaderService
from domains.video.domain.models.video import Video
from infrastructure.database.session import get_session
from infrastructure.runtime.site_config_manager import get_effective_site_catalog
from infrastructure.scheduling.base import BaseTask, TaskRegistry

logger = logging.getLogger(__name__)

_DEFAULT_MAX_WORKERS = 8


@TaskRegistry.register(interval=60 * 24, unit='minutes', start_immediately=True)
class ThumbnailRefreshTask(BaseTask):
    """Periodically backfill thumbnail cache for sites supporting offline thumbnails."""

    def __init__(self, thumbnail_downloader: ThumbnailDownloaderService | None = None):
        self._thumbnail_downloader = thumbnail_downloader or ThumbnailDownloaderService()

    def _batch_check_thumbnails(self, video_ids: list[int]) -> set[int]:
        """Return video IDs already present in the local thumbnail index."""
        existing_ids = set()
        batch_groups: dict[str, list[int]] = {}
        for video_id in video_ids:
            batch_dir = self._thumbnail_downloader._get_batch_dir(video_id)
            batch_groups.setdefault(batch_dir, []).append(video_id)

        for batch_dir, ids_in_batch in batch_groups.items():
            batch_index = self._thumbnail_downloader._get_batch_index(batch_dir)
            existing_ids.update(video_id for video_id in ids_in_batch if video_id in batch_index)
        return existing_ids

    @staticmethod
    def _get_refresh_targets() -> list[tuple[str, str]]:
        """Build refresh targets from the effective site catalog."""
        catalog = get_effective_site_catalog()
        targets: list[tuple[str, str]] = []
        for site_name, site_info in catalog.items():
            if not isinstance(site_info, dict):
                continue
            metadata = site_info.get('metadata') or {}
            if not site_info.get('enabled', True) or not metadata.get('offline_thumbnails_download', False):
                continue
            domains = site_info.get('domains') or []
            primary_domain = next(
                (str(domain).strip().lower() for domain in domains if str(domain or '').strip()),
                None,
            )
            if primary_domain:
                targets.append((str(site_name).strip().lower(), f'%{primary_domain}%'))
        return targets

    @staticmethod
    def _get_site_max_workers(site_name: str) -> int:
        del site_name
        return _DEFAULT_MAX_WORKERS

    @staticmethod
    def _get_stored_thumbnail_url(video: Video) -> str | None:
        stored_thumbnail = str(video.thumbnail or '').strip()
        return stored_thumbnail or None

    def _fetch_thumbnail_url_from_page(self, video: Video, site_name: str) -> str | None:
        return self._thumbnail_downloader.fetch_thumbnail_url_from_page(video.id, video.url, site_name)

    def _resolve_thumbnail_url(self, video: Video, site_name: str) -> str | None:
        return self._get_stored_thumbnail_url(video) or self._fetch_thumbnail_url_from_page(video, site_name)

    def run(self):
        try:
            return self._run()
        finally:
            self._thumbnail_downloader.close()

    def _run(self):
        logger.info('[ThumbnailRefreshTask] Start refreshing video thumbnails')

        batch_size = 100
        processed_count = 0
        total_checked = 0
        refresh_targets = self._get_refresh_targets()

        if not refresh_targets:
            logger.info('[ThumbnailRefreshTask] No enabled sites require thumbnail refresh')
            return

        for site_name, url_pattern in refresh_targets:
            max_workers = self._get_site_max_workers(site_name)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                last_id: int | None = None
                site_checked = 0

                with get_session() as session:
                    total_site_videos = session.scalar(
                        select(func.count(Video.id)).where(Video.url.like(url_pattern)),
                    )

                logger.info(
                    '[ThumbnailRefreshTask] Total %s videos to check: %d',
                    site_name,
                    total_site_videos,
                )

                while True:
                    with get_session() as session:
                        query = select(Video).where(Video.url.like(url_pattern)).order_by(Video.id.desc())
                        if last_id is not None:
                            query = query.where(Video.id < last_id)
                        rows: list[Video] = session.scalars(query.limit(batch_size)).all()

                    if not rows:
                        break

                    video_ids = [video.id for video in rows]
                    existing_thumbnails = self._batch_check_thumbnails(video_ids)

                    videos_to_process = []
                    for video in rows:
                        total_checked += 1
                        site_checked += 1
                        if video.id not in existing_thumbnails:
                            videos_to_process.append(video)

                    if videos_to_process:
                        futures = [
                            executor.submit(self._process_single_video, video, site_name) for video in videos_to_process
                        ]

                        for future in as_completed(futures):
                            try:
                                future.result()
                                processed_count += 1
                            except Exception as e:  # task boundary -- prevent single failure from crashing scheduler
                                logger.exception(
                                    '[ThumbnailRefreshTask] error processing video: %s',
                                    e,
                                )

                    if total_site_videos > 0:
                        progress_pct = site_checked / total_site_videos * 100
                        logger.info(
                            '[ThumbnailRefreshTask] Site %s batch checked %d/%d videos (%.1f%%), processed %d thumbnails',
                            site_name,
                            min(total_site_videos, site_checked),
                            total_site_videos,
                            progress_pct,
                            processed_count,
                        )

                    last_id = rows[-1].id

        logger.info(
            '[ThumbnailRefreshTask] Finished: checked %d videos, processed %d thumbnails',
            total_checked,
            processed_count,
        )

    def _process_single_video(self, video: Video, site_name: str) -> None:
        try:
            stored_thumbnail_url = self._get_stored_thumbnail_url(video)
            thumbnail_url = stored_thumbnail_url or self._fetch_thumbnail_url_from_page(video, site_name)
            if not thumbnail_url:
                logger.warning(
                    '[ThumbnailRefreshTask] No thumbnail found for site=%s video id=%s',
                    site_name,
                    video.id,
                )
                return

            downloaded_path = self._thumbnail_downloader.download_thumbnail(
                video.id,
                thumbnail_url,
                site_name,
                source_url=video.url,
            )
            if downloaded_path:
                logger.info(
                    '[ThumbnailRefreshTask] Downloaded thumbnail for site=%s video id=%s',
                    site_name,
                    video.id,
                )
                return

            if stored_thumbnail_url:
                page_thumbnail_url = self._fetch_thumbnail_url_from_page(video, site_name)
                if page_thumbnail_url and page_thumbnail_url != stored_thumbnail_url:
                    downloaded_path = self._thumbnail_downloader.download_thumbnail(
                        video.id,
                        page_thumbnail_url,
                        site_name,
                        source_url=video.url,
                    )
                    if downloaded_path:
                        logger.info(
                            '[ThumbnailRefreshTask] Downloaded thumbnail from page fallback for site=%s video id=%s',
                            site_name,
                            video.id,
                        )
                        return

            logger.warning(
                '[ThumbnailRefreshTask] Failed to cache thumbnail for site=%s video id=%s',
                site_name,
                video.id,
            )

        except Exception as e:  # task boundary -- prevent single failure from crashing scheduler
            logger.warning(
                '[ThumbnailRefreshTask] Failed to process site=%s video id=%s url=%s: %s',
                site_name,
                video.id,
                video.url,
                e,
            )
