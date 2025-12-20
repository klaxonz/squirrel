import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

import httpx
from sqlalchemy import select

from schedule.task import TaskRegistry, BaseTask
from core.database import get_session
from core.config import settings
from models.video import Video
from core.extraction.services.thumbnail_downloader import thumbnail_downloader_service

logger = logging.getLogger()

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


# @TaskRegistry.register(interval=60 * 24, unit='minutes', start_immediately=True)
class ThumbnailRefreshTask(BaseTask):
    """定时补全视频封面缓存（仅处理 pornhub 视频）。"""

    @classmethod
    def _load_existing_thumbnail_ids(cls) -> set[str]:
        thumbnails_dir = str(settings.thumbnails_dir)
        if not os.path.isdir(thumbnails_dir):
            return set()
        existing_ids: set[str] = set()

        for entry in os.listdir(thumbnails_dir):
            batch_path = os.path.join(thumbnails_dir, entry)
            if not (os.path.isdir(batch_path) and entry.startswith("batch_")):
                continue

            for filename in os.listdir(batch_path):
                full_path = os.path.join(batch_path, filename)
                if not os.path.isfile(full_path):
                    continue
                name, _ = os.path.splitext(filename)
                if name:
                    existing_ids.add(name)

        return existing_ids

    @classmethod
    def _extract_thumbnail_url(cls, html: str) -> Optional[str]:
        """从页面 JSON-LD 结构化数据中提取 thumbnailUrl"""
        match = re.search(r'<script\s+type=["\']application/ld\+json["\']>([^<]+)</script>', html)
        if not match:
            return None
        try:
            data = json.loads(match.group(1))
            return data.get('thumbnailUrl')
        except (json.JSONDecodeError, TypeError):
            return None

    @classmethod
    def run(cls):
        logger.info("[ThumbnailRefreshTask] Start refreshing video thumbnails")

        batch_size = 30
        last_id: int | None = None
        max_workers = 5

        existing_thumbnail_ids = cls._load_existing_thumbnail_ids()
        logger.info("[ThumbnailRefreshTask] Found %d existing thumbnails", len(existing_thumbnail_ids))

        with get_session() as session:
            pornhub_video_ids = set(
                str(vid) for vid in session.scalars(
                    select(Video.id).where(Video.url.like('%pornhub.com%'))
                ).all()
            )

        missing_ids = pornhub_video_ids - existing_thumbnail_ids
        total_videos = len(pornhub_video_ids)
        need_process = len(missing_ids)

        logger.info(
            "[ThumbnailRefreshTask] Total pornhub videos: %d, need to process: %d",
            total_videos,
            need_process
        )

        if need_process <= 0:
            logger.info("[ThumbnailRefreshTask] No videos need processing, skipping")
            return

        processed_count = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while True:
                with get_session() as session:
                    query = select(Video).where(Video.url.like('%pornhub.com%')).order_by(Video.id)
                    if last_id is not None:
                        query = query.where(Video.id > last_id)
                    rows: List[Video] = session.scalars(query.limit(batch_size)).all()

                if not rows:
                    break

                videos_to_process = [v for v in rows if str(v.id) not in existing_thumbnail_ids]

                if videos_to_process:
                    future_to_video = {
                        executor.submit(cls._process_single_video, video): video
                        for video in videos_to_process
                    }

                    for future in as_completed(future_to_video):
                        video = future_to_video[future]
                        try:
                            future.result()
                        except Exception as e:
                            logger.exception(
                                "[ThumbnailRefreshTask] error processing video id=%s: %s",
                                getattr(video, "id", None),
                                e,
                            )
                        processed_count += 1
                        progress_pct = (processed_count / need_process * 100) if need_process > 0 else 100
                        logger.info(
                            "[ThumbnailRefreshTask] Progress: %d/%d (%.1f%%)",
                            processed_count,
                            need_process,
                            progress_pct
                        )

                last_id = rows[-1].id

        logger.info("[ThumbnailRefreshTask] Finished refreshing video thumbnails")

    @classmethod
    def _process_single_video(cls, video: Video) -> None:
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True, headers=_HEADERS) as client:
                resp = client.get(video.url)

            if resp.status_code != 200:
                logger.warning(
                    "[ThumbnailRefreshTask] Failed to fetch page: video id=%s status=%s",
                    video.id,
                    resp.status_code
                )
                return

            thumbnail_url = cls._extract_thumbnail_url(resp.text)
            if not thumbnail_url:
                logger.warning("[ThumbnailRefreshTask] No thumbnail found for video id=%s", video.id)
                return

            thumbnail_downloader_service.download_thumbnail(video.id, thumbnail_url)
            logger.info("[ThumbnailRefreshTask] Downloaded thumbnail for video id=%s", video.id)

        except Exception as e:
            logger.warning(
                "[ThumbnailRefreshTask] Failed to process video id=%s url=%s: %s",
                video.id,
                video.url,
                e,
            )
