import logging
import os
from datetime import datetime

from sqlalchemy import select

from core.config import settings
from core.database import get_session
from models.video_thumbnail_local_index import VideoThumbnailLocalIndex
from services.video.extraction.thumbnail.storage import ThumbnailStorage

logger = logging.getLogger(__name__)


class ThumbnailLocalIndexRepository:
    """Database index for local thumbnail files."""

    def __init__(self, storage: ThumbnailStorage) -> None:
        self._storage = storage

    def upsert(self, video_id: int, batch_name: str, filename: str, exists: bool = True) -> None:
        now = datetime.now()
        with get_session() as session:
            record = session.scalars(
                select(VideoThumbnailLocalIndex).where(VideoThumbnailLocalIndex.video_id == video_id),
            ).first()
            if record is None:
                session.add(VideoThumbnailLocalIndex(
                    video_id=video_id,
                    batch_name=batch_name,
                    filename=filename,
                    exists=exists,
                    indexed_at=now,
                    created_at=now,
                    updated_at=now,
                ))
                return

            record.batch_name = batch_name
            record.filename = filename
            record.exists = exists
            record.indexed_at = now
            record.updated_at = now

    def get_local_thumbnail_path_map(
        self,
        indexed_items: list[tuple[int, str | None, str | None]],
    ) -> dict[int, str]:
        video_ids = [video_id for video_id, _remote_url, _video_url in indexed_items]
        if not video_ids:
            return {}

        with get_session() as session:
            rows = session.execute(
                select(
                    VideoThumbnailLocalIndex.video_id,
                    VideoThumbnailLocalIndex.batch_name,
                    VideoThumbnailLocalIndex.filename,
                ).where(
                    VideoThumbnailLocalIndex.video_id.in_(video_ids),
                    VideoThumbnailLocalIndex.exists.is_(True),
                ),
            ).all()

        results: dict[int, str] = {}
        for row in rows:
            file_path = os.path.join(str(settings.thumbnails_dir), row.batch_name, row.filename)
            if os.path.exists(file_path):
                results[row.video_id] = self._storage.build_static_thumbnail_url(row.batch_name, row.filename)
                continue

            self.upsert(row.video_id, row.batch_name, row.filename, exists=False)

        return results

