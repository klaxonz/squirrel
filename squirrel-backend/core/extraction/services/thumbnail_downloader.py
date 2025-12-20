"""
缩略图下载服务 - 负责下载缩略图到本地
"""
import logging
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

from core.config import settings
from utils.url_helper import get_site_from_url
from core.site_config_manager import get_effective_site_catalog
from common.site_constants import SITE_META_OFFLINE_THUMBNAILS_DOWNLOAD, SITE_META_OFFLINE_THUMBNAILS_DISPLAY

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


class ThumbnailDownloaderService:
    """
    缩略图下载服务

    职责：
    - 检查站点配置
    - 下载缩略图到本地
    - 管理缩略图存储目录
    """

    def __init__(self):
        self._http_client: Optional[httpx.Client] = None

    def _get_http_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(
                timeout=30.0,
                follow_redirects=True,
                headers=_DEFAULT_HEADERS,
            )
        return self._http_client

    def download_thumbnail(
        self,
        video_id: int,
        thumbnail_url: str,
        site_name: Optional[str] = None
    ) -> Optional[str]:
        """
        下载缩略图到本地

        Args:
            video_id: 视频ID
            thumbnail_url: 缩略图URL
            site_name: 站点名称（可选，用于检查配置）

        Returns:
            本地文件路径，失败返回 None
        """
        if not thumbnail_url:
            return None

        if site_name and not self._should_download(site_name):
            logger.debug(f"Thumbnail download disabled for site: {site_name}")
            return None

        try:
            batch_dir = self._get_batch_dir(video_id)
            os.makedirs(batch_dir, exist_ok=True)

            ext = self._get_extension(thumbnail_url)
            file_path = os.path.join(batch_dir, f"{video_id}{ext}")

            if os.path.exists(file_path):
                logger.debug(f"Thumbnail already exists: {file_path}")
                return file_path

            client = self._get_http_client()
            resp = client.get(thumbnail_url)

            if resp.status_code != 200:
                logger.warning(
                    f"Failed to download thumbnail: video_id={video_id}, "
                    f"status={resp.status_code}, url={thumbnail_url[:80]}"
                )
                return None

            content_type = resp.headers.get("content-type", "")
            if content_type and not content_type.startswith("image/"):
                logger.warning(
                    f"Invalid content type for thumbnail: video_id={video_id}, "
                    f"content_type={content_type}"
                )
                return None

            with open(file_path, "wb") as f:
                f.write(resp.content)

            logger.info(f"Thumbnail downloaded: video_id={video_id}, path={file_path}")
            return file_path

        except Exception as e:
            logger.warning(
                f"Failed to download thumbnail: video_id={video_id}, "
                f"url={thumbnail_url[:80]}, error={e}"
            )
            return None

    def enqueue_download(
        self,
        video_id: int,
        thumbnail_url: str,
        site_name: str
    ) -> Optional[str]:
        """
        下载缩略图（同步执行）

        Args:
            video_id: 视频ID
            thumbnail_url: 缩略图URL
            site_name: 站点名称

        Returns:
            本地文件路径，失败返回 None
        """
        return self.download_thumbnail(video_id, thumbnail_url, site_name)

    def _should_download(self, site_name: str) -> bool:
        """检查是否应该下载缩略图"""
        try:
            catalog = get_effective_site_catalog()
            site_info = catalog.get(site_name.lower(), {})
            metadata = site_info.get("metadata", {})
            return metadata.get(SITE_META_OFFLINE_THUMBNAILS_DOWNLOAD, False)
        except Exception as e:
            logger.warning(f"Failed to check thumbnail config: {e}")
            return False

    def _get_batch_dir(self, video_id: int) -> str:
        """获取视频所属的 batch 目录"""
        batch_num = (video_id - 1) // BATCH_SIZE + 1
        batch_name = f"batch_{batch_num:03d}"
        return os.path.join(str(settings.thumbnails_dir), batch_name)

    def _get_extension(self, url: str) -> str:
        """从 URL 中提取文件扩展名"""
        try:
            parsed = urlparse(url)
            path = parsed.path
            _, ext = os.path.splitext(path)
            if ext and ext.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"):
                return ext.lower()
        except Exception:
            pass
        return ".jpg"

    def thumbnail_exists(self, video_id: int) -> bool:
        """检查缩略图是否已存在"""
        batch_dir = self._get_batch_dir(video_id)
        if not os.path.isdir(batch_dir):
            return False

        for filename in os.listdir(batch_dir):
            name, _ = os.path.splitext(filename)
            if name == str(video_id):
                return True
        return False

    def _get_local_thumbnail_path(self, video_id: int) -> Optional[str]:
        """获取本地封面的静态URL路径"""
        batch_dir = self._get_batch_dir(video_id)
        if not os.path.isdir(batch_dir):
            return None

        batch_num = (video_id - 1) // BATCH_SIZE + 1
        batch_name = f"batch_{batch_num:03d}"

        for filename in os.listdir(batch_dir):
            name, _ = os.path.splitext(filename)
            if name == str(video_id):
                return f"/static/thumbnails/{batch_name}/{filename}"
        return None

    def _should_use_offline(self, site_name: str) -> bool:
        """检查是否应该使用离线封面"""
        try:
            catalog = get_effective_site_catalog()
            site_info = catalog.get(site_name.lower(), {})
            metadata = site_info.get("metadata", {})
            return metadata.get(SITE_META_OFFLINE_THUMBNAILS_DISPLAY, False)
        except Exception as e:
            logger.warning(f"Failed to check thumbnail display config: {e}")
            return False

    def get_thumbnail_url(self, video_id: int, remote_url: Optional[str], video_url: Optional[str] = None) -> Optional[str]:
        """
        获取封面的完整URL

        Args:
            video_id: 视频ID
            remote_url: 远程封面URL
            video_url: 视频URL（用于获取站点名称）

        Returns:
            本地静态路径或远程URL
        """
        if not remote_url:
            return None

        site_name = get_site_from_url(video_url) if video_url else None

        if site_name and self._should_use_offline(site_name):
            local_path = self._get_local_thumbnail_path(video_id)
            if local_path:
                return local_path

        return remote_url


thumbnail_downloader_service = ThumbnailDownloaderService()
