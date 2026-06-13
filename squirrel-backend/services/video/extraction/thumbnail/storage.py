import os
import time
from collections import OrderedDict
from urllib.parse import urlparse

from core.config import settings

BATCH_SIZE = 1000
SUPPORTED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif')
BATCH_INDEX_CACHE_TTL = 300.0
BATCH_INDEX_CACHE_MAX_BATCHES = 64


class ThumbnailStorage:
    """Local thumbnail filesystem storage."""

    def __init__(self) -> None:
        self._batch_index_cache: OrderedDict[str, tuple[dict[int, str], float]] = OrderedDict()

    def get_batch_dir(self, video_id: int) -> str:
        batch_num = (video_id - 1) // BATCH_SIZE + 1
        batch_name = f'batch_{batch_num:03d}'
        return os.path.join(str(settings.thumbnails_dir), batch_name)

    def get_extension(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path
        _, ext = os.path.splitext(path)
        if ext and ext.lower() in SUPPORTED_EXTENSIONS:
            return ext.lower()
        return '.jpg'

    def build_static_thumbnail_url(self, batch_name: str, filename: str) -> str:
        return f'/static/thumbnails/{batch_name}/{filename}'

    def scan_batch_index(self, batch_dir: str) -> dict[int, str]:
        if not os.path.isdir(batch_dir):
            return {}

        index: dict[int, str] = {}
        with os.scandir(batch_dir) as it:
            for entry in it:
                if not entry.is_file():
                    continue
                name = entry.name
                base, ext = os.path.splitext(name)
                if ext.lower() not in SUPPORTED_EXTENSIONS:
                    continue
                try:
                    video_id = int(base)
                except ValueError:
                    continue
                index[video_id] = name
        return index

    def get_batch_index(self, batch_dir: str) -> dict[int, str]:
        now = time.time()
        cached = self._batch_index_cache.get(batch_dir)
        if cached is not None:
            index, cached_at = cached
            if now - cached_at <= BATCH_INDEX_CACHE_TTL:
                self._batch_index_cache.move_to_end(batch_dir)
                return index

        index = self.scan_batch_index(batch_dir)
        self._batch_index_cache[batch_dir] = (index, now)
        self._batch_index_cache.move_to_end(batch_dir)
        self._evict_batch_index_cache()
        return index

    def upsert_batch_index_entry(self, batch_dir: str, video_id: int, filename: str) -> None:
        cached = self._batch_index_cache.get(batch_dir)
        if cached is None:
            return
        index, _ = cached
        index[video_id] = filename
        self._batch_index_cache[batch_dir] = (index, time.time())
        self._batch_index_cache.move_to_end(batch_dir)

    def thumbnail_exists(self, video_id: int) -> bool:
        batch_dir = self.get_batch_dir(video_id)
        return video_id in self.get_batch_index(batch_dir)

    def existing_thumbnail_ids(self, video_ids: list[int]) -> set[int]:
        existing_ids: set[int] = set()
        batch_groups: dict[str, list[int]] = {}
        for video_id in video_ids:
            batch_groups.setdefault(self.get_batch_dir(video_id), []).append(video_id)

        for batch_dir, ids_in_batch in batch_groups.items():
            batch_index = self.get_batch_index(batch_dir)
            existing_ids.update(video_id for video_id in ids_in_batch if video_id in batch_index)

        return existing_ids

    def get_local_thumbnail_path(self, video_id: int, remote_url: str | None = None) -> str | None:
        batch_dir = self.get_batch_dir(video_id)
        batch_name = os.path.basename(batch_dir)

        if remote_url:
            filename = f'{video_id}{self.get_extension(remote_url)}'
            file_path = os.path.join(batch_dir, filename)
            if os.path.exists(file_path):
                return self.build_static_thumbnail_url(batch_name, filename)
            return None

        filename = self.get_batch_index(batch_dir).get(video_id)
        if filename is None:
            return None
        return self.build_static_thumbnail_url(batch_name, filename)

    def target_file_path(self, video_id: int, thumbnail_url: str) -> tuple[str, str, str]:
        batch_dir = self.get_batch_dir(video_id)
        os.makedirs(batch_dir, exist_ok=True)
        filename = f'{video_id}{self.get_extension(thumbnail_url)}'
        return batch_dir, os.path.basename(batch_dir), os.path.join(batch_dir, filename)

    def _evict_batch_index_cache(self) -> None:
        while len(self._batch_index_cache) > BATCH_INDEX_CACHE_MAX_BATCHES:
            self._batch_index_cache.popitem(last=False)

