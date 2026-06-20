"""Meilisearch 视频索引器:增量 upsert(after_commit 直写)+ 全量重建 + 召回。

设计要点:
- after_commit 直写失败仅告警,不影响主流程(写入路径不阻塞);定期全量重建兜底。
- 召回只返回 video_id 集合,权限/分类(阅读状态)过滤交给 PG 实时 join
  (UserSubscription x SubscriptionVideo x Video),不进 Meilisearch。
- 文档把关联频道名/演员名合并进来,实现"跨表搜索"。
- recall() 支持结构化过滤下沉:domain(数组 IN)、duration(数值范围)、time_range(转 publish_ts 范围)。
- recall_page() 支持 keyset 游标分页:浏览场景按 publish_ts:desc, id:desc 全序召回一页,
  PG 在该页上做权限/category 过滤;不足一页时由 service 层循环召回补足。
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timedelta
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

# duration 档位 → (下界秒, 上界秒);上界 None 表示无上界
_DURATION_BOUNDS: dict[str, tuple[int, int | None]] = {
    'short': (0, 299),
    'medium': (300, 1800),
    'long': (1801, None),
}

# 游标命名空间 key:每个 key 对应一种排序语义,游标内嵌此标识。
# 切换排序时前端会清游标;这里再做一道后端校验:decode 出的 key 与当前请求排序键不符
# (例如 URL 直连残留的老游标)→ 视为失效返回首页,避免串号跳页。
#   p = 按发布时间(publish_date/publish_ts)排序的视频游标
#   c = 按抓取时间(created_at/created_ts)排序的视频游标
#   h = read(VideoHistory.end_time)交互游标
#   i = liked/later(VideoInteraction.created_at)交互游标
_CURSOR_KEY_PUBLISH = 'p'
_CURSOR_KEY_CREATED = 'c'
_CURSOR_KEY_HISTORY = 'h'
_CURSOR_KEY_INTERACTION = 'i'
_CURSOR_KEYS = (_CURSOR_KEY_PUBLISH, _CURSOR_KEY_CREATED, _CURSOR_KEY_HISTORY, _CURSOR_KEY_INTERACTION)


def compute_time_range_cutoff(time_range: str, *, now: datetime | None = None) -> int | None:
    """把 time_range 档位转成 unix 秒下界;all/未知返回 None(不过滤)。

    today: 当天 00:00 起;week: 本周一 00:00 起;month: 本月 1 日 00:00 起;year: 本年 1 月 1 日起。
    """
    if time_range == 'all':
        return None
    now = now or datetime.now()
    if time_range == 'today':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == 'week':
        # isoweekday: 周一=1 ... 周日=7
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == 'month':
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif time_range == 'year':
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        return None
    return int(start.timestamp())


def _build_recall_filter(
    *,
    domains: list[str] | None,
    time_range: str,
    duration: str,
    category: str = 'all',
    now: datetime | None = None,
    sort_by: str = 'publish_date',
) -> list[str]:
    """构建 Meili filter 表达式列表(隐式 AND)。

    返回空列表表示无过滤。每个元素是一个 filter 字符串,Meili 对 list 元素做 AND。

    category='preview' 时放行未来视频(该 tab 语义即"预告");其余 category(含 all)
    一律追加 publish_ts <= now 的上界,避免把尚未发布的视频召回进首页/搜索结果。

    time_range 下界按 sort_by 选择字段:按抓取日期(created_at)排序时用 created_ts,
    其余用 publish_ts —— 排序键与筛选语义保持一致。上界 publish_ts <= now 始终不变
    (排除未发布视频是发布语义,与排序键无关)。
    """
    time_field = 'created_ts' if sort_by == 'created_at' else 'publish_ts'
    filters: list[str] = []
    if domains:
        # domain IN ["a", "b"];值需双引号包裹(支持含点号的域名)
        quoted = ', '.join(f'"{d}"' for d in domains if d)
        if quoted:
            filters.append(f'domain IN [{quoted}]')
    if duration in _DURATION_BOUNDS:
        lo, hi = _DURATION_BOUNDS[duration]
        filters.append(f'duration >= {lo}')
        if hi is not None:
            filters.append(f'duration <= {hi}')
    cutoff = compute_time_range_cutoff(time_range)
    if cutoff is not None:
        filters.append(f'{time_field} >= {cutoff}')
    # 未来视频只在 preview tab 显式展示;其余场景(all/未读/搜索等)一律排除未发布视频
    if category != 'preview':
        now_ts = int((now or datetime.now()).timestamp())
        filters.append(f'publish_ts <= {now_ts}')
    return filters


def encode_cursor(key: str, ts: int, video_id: int) -> str:
    """把 (key, ts, id) 编码成对前端透明的 base64 字符串。

    key 标识游标命名空间(见 _CURSOR_KEY_* 常量),防止不同排序语义的游标串用。
    """
    raw = f'{key}:{ts}:{video_id}'.encode()
    return base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')


def decode_cursor(cursor: str) -> tuple[str, int, int] | None:
    """解码游标,返回 (key, ts, id);格式非法(含旧版 2 段游标)返回 None。

    旧版游标为 `{ts}:{id}` 两段,这里会因 split 出非 3 段而返回 None,
    调用方据此回退到首页 —— 等价于"老游标自然失效"。
    """
    try:
        padded = cursor + '=' * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded.encode('ascii')).decode('utf-8')
        key_str, ts_str, id_str = raw.split(':', 2)
        if key_str not in _CURSOR_KEYS:
            return None
        return key_str, int(ts_str), int(id_str)
    except (ValueError, IndexError, TypeError):
        logger.warning('invalid cursor ignored: %s', cursor)
        return None


def decode_cursor_for_key(cursor: str | None, expected_key: str) -> tuple[int, int] | None:
    """解码游标并校验 key 是否匹配预期命名空间;不匹配或非法返回 None。

    统一调用点写法:返回 None → 不施加 cursor 条件(回首页)。
    """
    if not cursor:
        return None
    decoded = decode_cursor(cursor)
    if decoded is None or decoded[0] != expected_key:
        return None
    return decoded[1], decoded[2]


class MeiliVideoIndexer:
    """将 video + 关联频道/演员写入 Meilisearch,并提供召回。"""

    def __init__(self, session_factory: sessionmaker | Any = None) -> None:
        self._session_factory = session_factory or get_session
        self._client = get_meili_client()
        self._index = self._client.index(settings.meili.index_videos)

    def _build_documents_batch(self, session: Session, video_ids: list[int]) -> list[dict[str, Any]]:
        """批量组装多个 video 的 Meilisearch 文档(reindex_all 优化版)。

        用 3 条聚合查询一次性取出本批所有 video 的基础字段 + subscription/creator 名,
        避免逐个 _build_document 的 Nx3 次 PG 往返。
        """
        if not video_ids:
            return []

        # 1. 批量取 video 基础字段
        videos = (
            session.execute(
                select(Video).where(
                    Video.id.in_(video_ids),
                    Video.is_deleted.is_(False),
                )
            )
            .scalars()
            .all()
        )
        if not videos:
            return []
        video_map = {v.id: v for v in videos}

        # 2. 批量取 subscription_names(一次查所有 video 的关联)
        sub_rows = session.execute(
            select(SubscriptionVideo.video_id, Subscription.name)
            .join(Subscription, Subscription.id == SubscriptionVideo.subscription_id)
            .where(
                SubscriptionVideo.video_id.in_(video_ids),
                Subscription.is_deleted.is_(False),
            )
        ).all()
        sub_map: dict[int, list[str]] = {}
        for vid, name in sub_rows:
            if name:
                sub_map.setdefault(vid, []).append(name)

        # 3. 批量取 creator_names
        creator_rows = session.execute(
            select(VideoCreator.video_id, Creator.name)
            .join(Creator, Creator.id == VideoCreator.creator_id)
            .where(
                VideoCreator.video_id.in_(video_ids),
                Creator.is_deleted.is_(False),
            )
        ).all()
        creator_map: dict[int, list[str]] = {}
        for vid, name in creator_rows:
            if name:
                creator_map.setdefault(vid, []).append(name)

        # 4. 按 video_ids 顺序组装文档
        docs: list[dict[str, Any]] = []
        for vid in video_ids:
            video = video_map.get(vid)
            if video is None:
                continue  # 已删除
            docs.append(
                {
                    'id': video.id,
                    'title': video.title or '',
                    'description': video.description or '',
                    'domain': video.domain or '',
                    'url': video.url or '',
                    'subscription_names': sub_map.get(vid, []),
                    'creator_names': creator_map.get(vid, []),
                    'duration': int(video.duration or 0),
                    'publish_ts': int(video.publish_date.timestamp()) if video.publish_date is not None else 0,
                    # 抓取时间,用于"按抓取日期"排序;created_at 不可空且有默认值,无需兜底
                    'created_ts': int(video.created_at.timestamp()),
                }
            )
        return docs

    def _build_document(self, session: Session, video_id: int) -> dict[str, Any] | None:
        """从 PG 组装单个 video 的 Meilisearch 文档;视频不存在/已删除返回 None。"""
        video = session.get(Video, video_id)
        if video is None or video.is_deleted:
            return None
        sub_names = (
            session.execute(
                select(Subscription.name)
                .join(SubscriptionVideo, SubscriptionVideo.subscription_id == Subscription.id)
                .where(
                    SubscriptionVideo.video_id == video_id,
                    Subscription.is_deleted.is_(False),
                ),
            )
            .scalars()
            .all()
        )
        creator_names = (
            session.execute(
                select(Creator.name)
                .join(VideoCreator, VideoCreator.creator_id == Creator.id)
                .where(
                    VideoCreator.video_id == video_id,
                    Creator.is_deleted.is_(False),
                ),
            )
            .scalars()
            .all()
        )
        doc: dict[str, Any] = {
            'id': video.id,
            'title': video.title or '',
            'description': video.description or '',
            'domain': video.domain or '',
            'url': video.url or '',
            'subscription_names': [name for name in sub_names if name],
            'creator_names': [name for name in creator_names if name],
            # duration: 秒,None/缺失统一存 0(避免范围过滤漏掉短/未知时长视频)
            'duration': int(video.duration or 0),
            # publish_ts: unix 秒,无 publish_date 时存 0(排到 desc 排序最底部,且参与正常游标分页,
            # 避免 null/缺失字段在 keyset 游标过滤里被排除导致这些视频永远看不到)
            'publish_ts': int(video.publish_date.timestamp()) if video.publish_date is not None else 0,
            # created_ts: 抓取时间 unix 秒,用于"按抓取日期"排序;created_at 不可空有默认值
            'created_ts': int(video.created_at.timestamp()),
        }
        return doc

    def upsert(self, video_id: int) -> None:
        """查询 PG 组装文档并推送 Meilisearch(id 相同则更新)。"""
        with self._session_factory() as session:
            doc = self._build_document(session, video_id)
        if doc is None:
            self.delete(video_id)
            return
        self._index.add_documents([doc])

    def upsert_safe(self, video_id: int) -> None:
        """after_commit 回调用:失败仅告警,不影响主流程(全量重建兜底)。"""
        try:
            self.upsert(video_id)
        except Exception:
            logger.warning('meili upsert failed video_id=%s (full reindex will catch up)', video_id, exc_info=True)

    def delete(self, video_id: int) -> None:
        """从 Meilisearch 删除文档(视频被软删/解绑时调用)。"""
        try:
            self._index.delete_document(str(video_id))
        except Exception:
            logger.warning('meili delete failed video_id=%s', video_id, exc_info=True)

    def reindex_all(self, batch_size: int = 500) -> int:
        """全量重建:遍历所有未删除视频,分批推送。用于首次回填和定期兜底。"""
        with self._session_factory() as session:
            video_ids = (
                session.execute(
                    select(Video.id).where(Video.is_deleted.is_(False)).order_by(Video.id),
                )
                .scalars()
                .all()
            )
        total = len(video_ids)
        total_batches = (total + batch_size - 1) // batch_size
        for offset in range(0, total, batch_size):
            batch_ids = video_ids[offset : offset + batch_size]
            with self._session_factory() as session:
                docs = self._build_documents_batch(session, batch_ids)
            if docs:
                self._index.add_documents(docs)
            logger.info('meili reindex batch %d/%d (pushed=%d)', offset // batch_size + 1, total_batches, len(docs))
        logger.info('meili reindex 完成,共 %d 个视频', total)
        return total

    def reindex_video_ids(self, video_ids: list[int]) -> int:
        """按 video_id 列表重建索引文档(用于订阅解绑/重命名等关联变更场景)。

        与 upsert 不同:这里批量查 PG + 单次 add_documents,避免 N 次往返。
        失败抛出,由调用方决定降级策略(解绑路径吞掉异常、靠全量重建兜底)。
        """
        if not video_ids:
            return 0
        with self._session_factory() as session:
            docs = [doc for vid in video_ids if (doc := self._build_document(session, vid)) is not None]
        if docs:
            self._index.add_documents(docs)
        return len(docs)

    def search(self, query: str, limit: int = 1000) -> list[int]:
        """文本召回:返回匹配的 video_id 列表(权限/排序回 PG)。

        简单版,不带结构化过滤;带 domain/time/duration 过滤请用 recall()。
        """
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

    def recall(
        self,
        query: str,
        *,
        domains: list[str] | None = None,
        time_range: str = 'all',
        duration: str = 'all',
        filter_ids: list[int] | None = None,
        limit: int = 1000,
        sort_by: str = 'publish_date',
        category: str = 'all',
    ) -> list[int]:
        """统一召回:文本匹配 + 结构化过滤(domain/time_range/duration 下沉 Meili)+ 排序。

        - query 非空:文本召回,按相关性返回(Meili 默认 ranking,忽略 sort_by)
        - query 为空:placeholder search,按 sort_by 返回(默认 publish_date 即 publish_ts:desc)
        - filter_ids:额外的 id 约束(read/liked/later 反向交集——PG 提供 per-user id 集合,
          Meili 在此范围内做文本召回)。None 表示不约束。
        - category='preview' 时放行未来视频;其余 category 一律排除未发布视频
        - 返回 video_id 列表,权限/category 过滤由调用方在 PG 侧处理
        - 失败抛出,由调用方决定降级(通常 fallback 到纯 PG 浏览路径或返回空)
        """
        filters = _build_recall_filter(
            domains=domains,
            time_range=time_range,
            duration=duration,
            category=category,
            sort_by=sort_by,
        )
        if filter_ids:
            # id IN [列表]:Meili 数字无需引号。列表过大时 Meili 会自行优化,但建议上游控制规模。
            id_list = ', '.join(str(i) for i in filter_ids)
            filters.append(f'id IN [{id_list}]')
        opt: dict[str, Any] = {'limit': limit}
        if filters:
            # 用 list 形式:Meili 隐式 AND,避免字符串拼接的转义/优先级 bug
            opt['filter'] = filters
        q = (query or '').strip()
        # 无搜索词时按 sort_by 召回(最新优先),让 PG 侧 LIMIT/OFFSET 拿到最近的 N 个。
        # 注意:搜索路径(has_query=True)永远走不进此分支,这里仅作 placeholder 浏览兜底。
        if not q:
            sort_field = 'created_ts' if sort_by == 'created_at' else 'publish_ts'
            opt['sort'] = [f'{sort_field}:desc']
        result = self._index.search(q, opt)
        hits = result.get('hits', []) if isinstance(result, dict) else getattr(result, 'hits', [])
        ids: list[int] = []
        for hit in hits:
            raw_id = hit.get('id') if isinstance(hit, dict) else None
            try:
                ids.append(int(raw_id))
            except (TypeError, ValueError):
                continue
        if len(ids) >= limit:
            logger.warning('meili recall hit limit=%d (可能丢结果,请调高 limit)', limit)
        return ids

    def recall_page(
        self,
        *,
        domains: list[str] | None = None,
        time_range: str = 'all',
        duration: str = 'all',
        cursor: str | None = None,
        limit: int = 50,
        category: str = 'all',
        sort_by: str = 'publish_date',
    ) -> tuple[list[int], str | None]:
        """keyset 游标分页召回(浏览场景,无文本匹配)。

        - sort: 按 sort_by 选 publish_ts:desc 或 created_ts:desc,id:desc 作次级键(全序,保证游标稳定)
        - cursor 非空:filter 追加复合游标条件 field<X OR (field=X AND id<Y);
          decode 出的 key 必须与当前 sort_by 命名空间匹配,否则视为失效(老游标/串用游标)
        - category='preview' 时放行未来视频;其余 category 一律排除未发布视频
        - 返回 (video_ids, next_cursor);next_cursor 为 None 表示无更多
        - 失败抛出,由调用方降级

        注意:limit 应略大于 page_size(如 page_size*2),给 PG 权限/category 过滤留缓冲,
        由 service 层循环补足到 page_size。
        """
        sort_field = 'created_ts' if sort_by == 'created_at' else 'publish_ts'
        expected_key = _CURSOR_KEY_CREATED if sort_by == 'created_at' else _CURSOR_KEY_PUBLISH
        filters = _build_recall_filter(
            domains=domains,
            time_range=time_range,
            duration=duration,
            category=category,
            sort_by=sort_by,
        )
        decoded = decode_cursor_for_key(cursor, expected_key)
        if decoded is not None:
            cursor_ts, cursor_id = decoded
            # 复合游标:严格小于 (cursor_ts, cursor_id) 的所有文档
            filters.append(
                f'({sort_field} < {cursor_ts} OR ({sort_field} = {cursor_ts} AND id < {cursor_id}))'
            )

        opt: dict[str, Any] = {
            'limit': limit,
            'sort': [f'{sort_field}:desc', 'id:desc'],
        }
        if filters:
            opt['filter'] = filters

        result = self._index.search('', opt)  # placeholder search = 浏览
        hits = result.get('hits', []) if isinstance(result, dict) else getattr(result, 'hits', [])

        ids: list[int] = []
        last_ts: int | None = None
        last_id: int | None = None
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            raw_id = hit.get('id')
            try:
                vid = int(raw_id)
            except (TypeError, ValueError):
                continue
            ids.append(vid)
            last_ts = int(hit.get(sort_field) or 0)
            last_id = vid

        # 有下一页的判定:本次召回满 limit,且拿到了最后一条的游标
        next_cursor = None
        if len(ids) >= limit and last_ts is not None and last_id is not None:
            next_cursor = encode_cursor(expected_key, last_ts, last_id)
        return ids, next_cursor


_indexer: MeiliVideoIndexer | None = None


def get_meili_video_indexer() -> MeiliVideoIndexer:
    """返回 MeiliVideoIndexer 单例(首次调用初始化,需已配置 MEILISEARCH_URL)。"""
    global _indexer
    if _indexer is None:
        _indexer = MeiliVideoIndexer()
    return _indexer


def register_meili_video_event_listener() -> None:
    """Subscribe the Meilisearch indexer to the ``video.saved`` domain event.

    This decouples the video persistence layer from the indexer: persistence
    fires ``DomainEvents.VIDEO_SAVED`` via the in-process dispatcher, and this
    listener (registered once at bootstrap, in both the web lifespan and the
    worker bootstrap) calls ``upsert_safe``. Idempotent -- safe to call from
    both startup paths; registration dedupes.
    """
    from shared_kernel.domain.events import DomainEvents, domain_events

    def _on_video_saved(payload: dict) -> None:
        video_id = payload.get('video_id')
        if video_id is None:
            return
        try:
            get_meili_video_indexer().upsert_safe(video_id)
        except Exception:
            logging.getLogger(__name__).warning(
                'meili upsert_safe failed video_id=%s (full reindex will catch up)', video_id, exc_info=True
            )

    domain_events.register(DomainEvents.VIDEO_SAVED, _on_video_saved)
