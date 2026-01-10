import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

import httpx
from sqlalchemy import select, func

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

# 全局 HTTP 客户端，复用连接
_shared_http_client: Optional[httpx.Client] = None
_client_lock_time = 0.0
_CLIENT_TTL = 300.0  # 5分钟

def _get_shared_http_client() -> httpx.Client:
    """获取共享的 HTTP 客户端"""
    global _shared_http_client, _client_lock_time

    now = time.time()
    if _shared_http_client is None or now - _client_lock_time > _CLIENT_TTL:
        if _shared_http_client:
            try:
                _shared_http_client.close()
            except:
                pass

        _shared_http_client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers=_HEADERS,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
        )
        _client_lock_time = now

    return _shared_http_client


@TaskRegistry.register(interval=60 * 24, unit='minutes', start_immediately=True)
class ThumbnailRefreshTask(BaseTask):
    """定时补全视频封面缓存（仅处理 pornhub 视频）。"""

    @classmethod
    def _batch_check_thumbnails(cls, video_ids: List[int]) -> set[int]:
        """
        批量检查多个视频的缩略图是否存在
        返回已存在缩略图的 video_id 集合
        """
        from core.extraction.services.thumbnail_downloader import thumbnail_downloader_service

        existing_ids = set()

        # 按 batch 分组，避免重复扫描同一目录
        batch_groups: dict[str, List[int]] = {}
        for video_id in video_ids:
            batch_dir = thumbnail_downloader_service._get_batch_dir(video_id)
            if batch_dir not in batch_groups:
                batch_groups[batch_dir] = []
            batch_groups[batch_dir].append(video_id)

        # 对每个 batch 一次性获取索引，然后检查所有 video_id
        for batch_dir, ids_in_batch in batch_groups.items():
            batch_index = thumbnail_downloader_service._get_batch_index(batch_dir)
            for video_id in ids_in_batch:
                if video_id in batch_index:
                    existing_ids.add(video_id)

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

        # 增大批次大小，减少数据库查询次数
        batch_size = 100
        last_id: int | None = None
        max_workers = 8  # 增加并发数
        processed_count = 0
        total_checked = 0

        with get_session() as session:
            # 获取总数用于进度显示
            total_pornhub_videos = session.scalar(
                select(func.count(Video.id)).where(Video.url.like('%pornhub.com%'))
            )

        logger.info("[ThumbnailRefreshTask] Total pornhub videos to check: %d", total_pornhub_videos)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while True:
                with get_session() as session:
                    query = select(Video).where(Video.url.like('%pornhub.com%')).order_by(Video.id.desc())
                    if last_id is not None:
                        query = query.where(Video.id < last_id)
                    rows: List[Video] = session.scalars(query.limit(batch_size)).all()

                if not rows:
                    break

                # 批量预加载缩略图索引，避免逐个检查
                video_ids = [video.id for video in rows]
                existing_thumbnails = cls._batch_check_thumbnails(video_ids)

                # 筛选需要处理的视频
                videos_to_process = []
                for video in rows:
                    total_checked += 1
                    if video.id not in existing_thumbnails:
                        videos_to_process.append(video)

                if videos_to_process:
                    # 并发处理视频下载，使用更大的并发数
                    futures = [
                        executor.submit(cls._process_single_video, video)
                        for video in videos_to_process
                    ]

                    for future in as_completed(futures):
                        try:
                            future.result()
                            processed_count += 1
                        except Exception as e:
                            logger.exception(
                                "[ThumbnailRefreshTask] error processing video: %s", e
                            )

                # 显示进度
                if total_pornhub_videos > 0:
                    progress_pct = (total_checked / total_pornhub_videos * 100)
                    logger.info(
                        "[ThumbnailRefreshTask] Progress: checked %d/%d videos (%.1f%%), processed %d thumbnails",
                        total_checked,
                        total_pornhub_videos,
                        progress_pct,
                        processed_count
                    )

                last_id = rows[-1].id

        logger.info(
            "[ThumbnailRefreshTask] Finished: checked %d videos, processed %d thumbnails",
            total_checked,
            processed_count
        )

    @classmethod
    def _process_single_video(cls, video: Video) -> None:
        try:
            # 使用共享的 HTTP 客户端，提高连接复用率
            client = _get_shared_http_client()
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

            # 下载缩略图时指定 site_name，启用配置检查
            thumbnail_downloader_service.download_thumbnail(video.id, thumbnail_url, "pornhub")
            logger.info("[ThumbnailRefreshTask] Downloaded thumbnail for video id=%s", video.id)

        except Exception as e:
            logger.warning(
                "[ThumbnailRefreshTask] Failed to process video id=%s url=%s: %s",
                video.id,
                video.url,
                e,
            )
