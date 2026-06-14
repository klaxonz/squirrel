"""Meilisearch 视频索引器：增量 upsert（after_commit 直写）+ 全量重建 + 召回。

设计要点：
- after_commit 直写失败仅告警，不影响主流程（写入路径不阻塞）；定期全量重建兜底。
- 召回只返回 video_id 集合，权限/分类/排序/分页交给 PG 的 user_video_feed join。
- 文档把关联频道名/演员名合并进来，实现"跨表搜索"——这样搜索时只需查 Video 一张表，
  不再需要 legacy 路径那套 EXISTS 相关子查询。
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from domains.subscription.domain.models.subscription import Subscription
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.video.domain.junctions.video_creator import VideoCreator
from domains.video.domain.models.creator import Creator
from domains.video.domain.models.video import Video
from infrastructure.config.settings import settings
from infrastructure.database.session import get_session
from infrastructure.search.meili import get_meili_client

logger = logging.getLogger(__name__)


class MeiliVideoIndexer:
    """将 video + 关联频道/演员写入 Meilisearch，并提供召回。"""

    def __init__(self, session_factory: sessionmaker | Any = None) -> None:
        self._session_factory = session_factory or get_session
        self._client = get_meili_client()
        self._index = self._client.index(settings.MEILISEARCH_INDEX_VIDEOS)

    def _build_document(self, session: Session, video_id: int) -> dict[str, Any] | None:
        """从 PG 组装单个 video 的 Meilisearch 文档；视频不存在/已删除返回 None。"""
        video = session.get(Video, video_id)
        if video is None or video.is_deleted:
            return None
        sub_names = session.execute(
            select(Subscription.name)
            .join(SubscriptionVideo, SubscriptionVideo.subscription_id == Subscription.id)
            .where(
                SubscriptionVideo.video_id == video_id,
                Subscription.is_deleted.is_(False),
            ),
        ).scalars().all()
        creator_names = session.execute(
            select(Creator.name)
            .join(VideoCreator, VideoCreator.creator_id == Creator.id)
            .where(
                VideoCreator.video_id == video_id,
                Creator.is_deleted.is_(False),
            ),
        ).scalars().all()
        return {
            'id': video.id,
            'title': video.title or '',
            'description': video.description or '',
            'domain': video.domain or '',
            'url': video.url or '',
            'subscription_names': [name for name in sub_names if name],
            'creator_names': [name for name in creator_names if name],
        }

    def upsert(self, video_id: int) -> None:
        """查询 PG 组装文档并推送 Meilisearch（id 相同则更新）。"""
        with self._session_factory() as session:
            doc = self._build_document(session, video_id)
        if doc is None:
            self.delete(video_id)
            return
        self._index.add_documents([doc])

    def upsert_safe(self, video_id: int) -> None:
        """after_commit 回调用：失败仅告警，不影响主流程（全量重建兜底）。"""
        try:
            self.upsert(video_id)
        except Exception:
            logger.warning('meili upsert failed video_id=%s (full reindex will catch up)', video_id, exc_info=True)

    def delete(self, video_id: int) -> None:
        """从 Meilisearch 删除文档（视频被软删/解绑时调用）。"""
        try:
            self._index.delete_document(str(video_id))
        except Exception:
            logger.warning('meili delete failed video_id=%s', video_id, exc_info=True)

    def reindex_all(self, batch_size: int = 500) -> int:
        """全量重建：遍历所有未删除视频，分批推送。用于首次回填和定期兜底。"""
        with self._session_factory() as session:
            video_ids = session.execute(
                select(Video.id).where(Video.is_deleted.is_(False)).order_by(Video.id),
            ).scalars().all()
        total = len(video_ids)
        total_batches = (total + batch_size - 1) // batch_size
        for offset in range(0, total, batch_size):
            batch_ids = video_ids[offset:offset + batch_size]
            with self._session_factory() as session:
                docs = [doc for vid in batch_ids if (doc := self._build_document(session, vid)) is not None]
            if docs:
                self._index.add_documents(docs)
            logger.info('meili reindex batch %d/%d (pushed=%d)', offset // batch_size + 1, total_batches, len(docs))
        logger.info('meili reindex 完成，共 %d 个视频', total)
        return total

    def reindex_video_ids(self, video_ids: list[int]) -> int:
        """按 video_id 列表重建索引文档（用于订阅解绑/重命名等关联变更场景）。

        与 upsert 不同：这里批量查 PG + 单次 add_documents，避免 N 次往返。
        失败抛出，由调用方决定降级策略（解绑路径吞掉异常、靠全量重建兜底）。
        """
        if not video_ids:
            return 0
        with self._session_factory() as session:
            docs = [doc for vid in video_ids if (doc := self._build_document(session, vid)) is not None]
        if docs:
            self._index.add_documents(docs)
        return len(docs)

    def search(self, query: str, limit: int = 1000) -> list[int]:
        """文本召回：返回匹配的 video_id 列表（权限/排序回 PG）。"""
        if not query or not query.strip():
            return []
        result = self._index.search(query, {'limit': limit})
        hits = result.get('hits', []) if isinstance(result, dict) else getattr(result, 'hits', [])
        ids: list[int] = []
        for hit in hits:
            raw_id = hit.get('id') if isinstance(hit, dict) else None
            try:
                ids.append(int(raw_id))
            except (TypeError, ValueError):
                continue
        return ids


_indexer: MeiliVideoIndexer | None = None


def get_meili_video_indexer() -> MeiliVideoIndexer:
    """返回 MeiliVideoIndexer 单例（首次调用初始化，需已配置 MEILISEARCH_URL）。"""
    global _indexer
    if _indexer is None:
        _indexer = MeiliVideoIndexer()
    return _indexer
