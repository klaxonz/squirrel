import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import httpx
from sqlalchemy import select

from schedule.task import TaskRegistry, BaseTask
from core.database import get_session
from core.config import settings
from models.video import Video
from models.links import SubscriptionVideo
from schemas.video.dto.video_dto import VideoExtractDto
from services.video_extraction.extractor import video_extractor
from core.extraction.handlers.video_handler import VideoExtractionHandler

logger = logging.getLogger()


@TaskRegistry.register(interval=60 * 24, unit='minutes', start_immediately=True)
class ThumbnailRefreshTask(BaseTask):
    """定时校验并补全视频封面缓存。

    - 遍历所有视频，尝试根据当前 thumbnail URL 下载封面到本地（受站点 metadata.offline_thumbnails_download 控制）。
    - 如果远程封面返回 404，则重新提取该视频详情以获取新的封面 URL，更新数据库后再尝试下载新的封面。
    """

    @classmethod
    def run(cls):
        logger.info("[ThumbnailRefreshTask] Start refreshing video thumbnails")
        
        batch_size = 500
        last_id: int | None = None
        max_workers = 100

        while True:
            with get_session() as session:
                query = select(Video).order_by(Video.id)
                if last_id is not None:
                    query = query.where(Video.id > last_id)
                rows: List[Video] = session.scalars(query.limit(batch_size)).all()

            if not rows:
                break

            # 每批使用线程池并发处理视频，避免单线程过慢
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_video = {
                    executor.submit(cls._process_single_video, video): video for video in rows
                }

                for future in as_completed(future_to_video):
                    video = future_to_video[future]
                    last_id = video.id
                    try:
                        future.result()
                    except Exception as e:
                        logger.exception(
                            "[ThumbnailRefreshTask] unexpected error while processing video id=%s: %s",
                            getattr(video, "id", None),
                            e,
                        )

        logger.info("[ThumbnailRefreshTask] Finished refreshing video thumbnails")

    @staticmethod
    def _process_single_video(video: Video) -> None:
        """处理单个视频的封面刷新逻辑（在线程池中调用）。"""
        if not video.thumbnail:
            return

        # 先根据与 _download_thumbnail 相同的规则检查本地文件是否已存在
        # 为了避免重复解析 URL 取扩展名，这里简单按常见扩展名顺序检查；
        # 如果在 handler 中最终写入的是不在此列表中的扩展名，也只是会多发一次 HTTP 请求，逻辑仍然正确。
        thumbnails_dir = str(settings.thumbnails_dir)
        exts = [".jpg", ".jpeg", ".png", ".webp"]
        for ext in exts:
            candidate = os.path.join(thumbnails_dir, f"{video.id}{ext}")
            if os.path.exists(candidate):
                # 本地已有封面文件，直接跳过
                return

        # 本地不存在封面文件，按之前的逻辑检查远程并决定是否重新提取或下载
        handler = VideoExtractionHandler()

        # 先轻量校验远程封面是否可访问，避免不必要的重新提取
        # 加一个浏览器 UA，避免部分图床因缺少 UA 返回 412 等错误
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        # 简单重试：最多 2 次（初次 + 重试 1 次），每次超时时间固定为 15s
        resp: httpx.Response | None = None

        try:
            for attempt in range(2):
                try:
                    resp = httpx.get(
                        video.thumbnail,
                        timeout=15.0,
                        follow_redirects=True,
                        headers=headers,
                    )
                    break
                except Exception as e:
                    logger.warning(
                        "[ThumbnailRefreshTask] thumbnail check failed (attempt %s) id=%s url=%s error=%s",
                        attempt + 1,
                        video.id,
                        video.thumbnail,
                        e,
                    )

            if resp is None:
                # 多次重试仍失败，等待下次任务再处理
                return

            if resp.status_code == 404:
                # 远程封面已失效：尝试重新提取视频详情获取新的 thumbnail
                ThumbnailRefreshTask._refresh_video_thumbnail_via_extraction(video)
                return

            if resp.status_code >= 400:
                logger.warning(
                    "[ThumbnailRefreshTask] thumbnail status %s for id=%s url=%s",
                    resp.status_code,
                    video.id,
                    video.thumbnail,
                )
                return

            # 远程可访问：尝试按站点配置下载到本地
            try:
                handler._download_thumbnail(video, video.thumbnail)  # type: ignore[attr-defined]
            except Exception as e:
                logger.warning(
                    "[ThumbnailRefreshTask] download thumbnail failed: id=%s url=%s error=%s",
                    video.id,
                    video.thumbnail,
                    e,
                )
        except Exception as e:
            logger.exception(
                "[ThumbnailRefreshTask] unexpected error while processing video id=%s: %s",
                getattr(video, "id", None),
                e,
            )

    @staticmethod
    def _refresh_video_thumbnail_via_extraction(video: Video) -> None:
        """重新提取视频详情以刷新 thumbnail，并尝试下载新的封面。

        仅在提取成功且产生新的 thumbnail 时才更新本地缓存，具体入库逻辑由
        VideoExtractionHandler 负责，这里只负责触发提取和后续下载。
        """
        try:
            # 尝试获取关联订阅，尽量还原上下文
            with get_session() as session:
                sv = session.scalars(
                    select(SubscriptionVideo).where(SubscriptionVideo.video_id == video.id)
                ).first()
                subscription_id = sv.subscription_id if sv else None

            params = VideoExtractDto(
                url=video.url,
                only_extract=True,
                subscribed=bool(subscription_id),
                subscription_id=subscription_id,
                is_extract_all=False,
                is_manual=False,
            )

            result = video_extractor.extract(params)
            if not getattr(result, "success", False):
                logger.warning(
                    "[ThumbnailRefreshTask] re-extract failed for video id=%s url=%s error=%s",
                    video.id,
                    video.url,
                    getattr(result, "error", None),
                )
                return

            # 重新从数据库读取视频，获取最新的 thumbnail
            with get_session() as session:
                fresh = session.get(Video, video.id)

            if not fresh or not fresh.thumbnail:
                return

            handler = VideoExtractionHandler()
            try:
                handler._download_thumbnail(fresh, fresh.thumbnail)  # type: ignore[attr-defined]
            except Exception as e:
                logger.warning(
                    "[ThumbnailRefreshTask] download refreshed thumbnail failed: id=%s url=%s error=%s",
                    fresh.id,
                    fresh.thumbnail,
                    e,
                )
        except Exception as e:
            logger.exception(
                "[ThumbnailRefreshTask] unexpected error when re-extracting video id=%s: %s",
                getattr(video, "id", None),
                e,
            )
