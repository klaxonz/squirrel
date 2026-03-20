"""
缩略图下载服务 - 负责下载缩略图到本地
"""
import logging
import os
import time
from collections import OrderedDict
from typing import Optional
from urllib.parse import urlparse

import httpx

from core.config import settings
from utils.url_helper import get_site_from_url
from core.site_config_manager import get_effective_site_catalog
from common.site_constants import SITE_META_OFFLINE_THUMBNAILS_DOWNLOAD, SITE_META_OFFLINE_THUMBNAILS_DISPLAY

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000
SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif")
_EFFECTIVE_CATALOG_CACHE_TTL = 10.0
_BATCH_INDEX_CACHE_TTL = 30.0
_BATCH_INDEX_CACHE_MAX_BATCHES = 64

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
        self._effective_catalog: Optional[dict] = None
        self._effective_catalog_cached_at = 0.0
        self._batch_index_cache: OrderedDict[str, tuple[dict[int, str], float]] = OrderedDict()

    def _get_http_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(
                timeout=30.0,
                follow_redirects=True,
                headers=_DEFAULT_HEADERS,
            )
        return self._http_client

    def _build_request_headers(self, site_name: Optional[str]) -> dict[str, str]:
        headers = dict(_DEFAULT_HEADERS)
        if not site_name:
            return headers

        site_info = self._get_effective_catalog().get(site_name.lower(), {})
        http_headers = (site_info.get("http") or {}).get("headers") or {}
        for key, value in http_headers.items():
            if value is not None:
                headers[str(key)] = str(value)

        referer = headers.get("Referer")
        if referer and "Origin" not in headers:
            try:
                parsed = urlparse(referer)
                if parsed.scheme and parsed.netloc:
                    headers["Origin"] = f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                pass

        return headers

    def _get_effective_catalog(self) -> dict:
        now = time.time()
        if (
            self._effective_catalog is None
            or now - self._effective_catalog_cached_at > _EFFECTIVE_CATALOG_CACHE_TTL
        ):
            self._effective_catalog = get_effective_site_catalog()
            self._effective_catalog_cached_at = now
        return self._effective_catalog

    def _evict_batch_index_cache(self) -> None:
        while len(self._batch_index_cache) > _BATCH_INDEX_CACHE_MAX_BATCHES:
            self._batch_index_cache.popitem(last=False)

    def _scan_batch_index(self, batch_dir: str) -> dict[int, str]:
        if not os.path.isdir(batch_dir):
            return {}

        index: dict[int, str] = {}
        with os.scandir(batch_dir) as it:
            for entry in it:
                if not entry.is_file():
                    continue
                name = entry.name
                base, ext = os.path.splitext(name)
                ext = ext.lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue
                try:
                    video_id = int(base)
                except ValueError:
                    continue
                index[video_id] = name
        return index

    def _get_batch_index(self, batch_dir: str) -> dict[int, str]:
        now = time.time()
        cached = self._batch_index_cache.get(batch_dir)
        if cached is not None:
            index, cached_at = cached
            if now - cached_at <= _BATCH_INDEX_CACHE_TTL:
                self._batch_index_cache.move_to_end(batch_dir)
                return index

        index = self._scan_batch_index(batch_dir)
        self._batch_index_cache[batch_dir] = (index, now)
        self._batch_index_cache.move_to_end(batch_dir)
        self._evict_batch_index_cache()
        return index

    def _upsert_batch_index_entry(self, batch_dir: str, video_id: int, filename: str) -> None:
        cached = self._batch_index_cache.get(batch_dir)
        if cached is None:
            return
        index, _ = cached
        index[video_id] = filename
        self._batch_index_cache[batch_dir] = (index, time.time())
        self._batch_index_cache.move_to_end(batch_dir)

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
            headers = self._build_request_headers(site_name)
            resp = client.get(thumbnail_url, headers=headers)

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

            self._upsert_batch_index_entry(batch_dir, video_id, os.path.basename(file_path))
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
            catalog = self._get_effective_catalog()
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
            if ext and ext.lower() in SUPPORTED_EXTENSIONS:
                return ext.lower()
        except Exception:
            pass
        return ".jpg"

    def thumbnail_exists(self, video_id: int) -> bool:
        """检查缩略图是否已存在"""
        batch_dir = self._get_batch_dir(video_id)
        return video_id in self._get_batch_index(batch_dir)

    def _get_local_thumbnail_path(self, video_id: int) -> Optional[str]:        
        """获取本地封面的静态URL路径"""
        batch_dir = self._get_batch_dir(video_id)
        batch_index = self._get_batch_index(batch_dir)
        filename = batch_index.get(video_id)
        if filename is None:
            return None
        batch_name = os.path.basename(batch_dir)
        return f"/static/thumbnails/{batch_name}/{filename}"

    def _should_use_offline(self, site_name: str) -> bool:
        """检查是否应该使用离线封面"""
        try:
            catalog = self._get_effective_catalog()
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
