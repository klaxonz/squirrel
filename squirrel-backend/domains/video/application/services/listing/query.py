from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from domains.video.application.services.listing.query_filters import (
    build_active_subscriptions_query,
    feed_category_predicate,
)
from domains.video.application.services.moderation.nsfw_policy import (
    resolve_effective_nsfw_filter as _default_resolve_effective_nsfw_filter,
)
from domains.video.application.services.search.meili_indexer import decode_cursor, encode_cursor
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.video.domain.models.video import Video
from domains.video.domain.models.video_history import VideoHistory
from domains.video.domain.models.video_interaction import VideoInteraction

# read/liked/later 的 interaction_type 映射
_CATEGORY_INTERACTION_TYPE: dict[str, int] = {
    'liked': 1,
    'later': 3,
}


class VideoListQueryService:
    def __init__(self, resolve_effective_nsfw_filter=None):
        resolve_nsfw_filter = resolve_effective_nsfw_filter or _default_resolve_effective_nsfw_filter
        self._build_active_subscriptions_query = (
            lambda **kwargs: build_active_subscriptions_query(
                **kwargs,
                resolve_effective_nsfw_filter_func=resolve_nsfw_filter,
            )
        )

    def filter_recalled_ids(
        self,
        session: Session,
        *,
        recalled_ids: list[int],
        user_id: int,
        show_nsfw: bool,
        subscription_id: int | None,
        category: str,
        nsfw: str,
        content_type: str,
        special: str,
    ) -> list[int]:
        """对 Meili 召回的 video_id 集合做 PG 权限 + category 过滤，保持召回顺序返回。

        PG 负责：
        - 权限（订阅/nsfw/special）走 active_subscriptions join
        - category（read/unread/liked/later/preview）走 feed_category_predicate EXISTS
        - content_type 走 active_subscriptions.c.subscription_type
        返回值按 recalled_ids 原始顺序去重（Meili 的排序即最终顺序）。

        注意：read/liked/later 场景下 category 过滤由上游 fetch_user_state_* 保证，
        此处传 category='all' 即可（避免重复 EXISTS）；unread 场景仍需 NOT EXISTS。
        """
        if not recalled_ids:
            return []

        active_subscriptions = self._build_active_subscriptions_query(
            user_id=user_id,
            subscription_id=subscription_id,
            nsfw=nsfw,
            show_nsfw=show_nsfw,
            special=special,
        )

        query_stmt = (
            select(Video.id)
            .select_from(Video)
            .join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
            .join(active_subscriptions, active_subscriptions.c.subscription_id == SubscriptionVideo.subscription_id)
            .where(
                Video.is_deleted.is_(False),
                Video.id.in_(recalled_ids),
            )
        )

        if content_type != 'all':
            query_stmt = query_stmt.where(active_subscriptions.c.subscription_type == content_type)

        if category and category not in ('all', 'read', 'liked', 'later'):
            # read/liked/later 的 category 语义已由上游 per-user 表保证，这里不再 EXISTS
            # all/preview 不需要 category 过滤；unread 需要 NOT EXISTS
            query_stmt = query_stmt.where(
                feed_category_predicate(
                    user_id,
                    category,
                    video_id_column=Video.id,
                    publish_date_column=Video.publish_date,
                )
            )

        # fan-out 去重（同一 video 多个订阅会多行），取 set
        matched = {row[0] for row in session.execute(query_stmt).all()}

        # 按召回顺序返回（Meili 的排序即最终顺序）
        return [vid for vid in recalled_ids if vid in matched]


video_list_query_service = VideoListQueryService()

# 模块级便捷函数
filter_recalled_ids = video_list_query_service.filter_recalled_ids


def fetch_special_follow_video_ids(
    session: Session,
    *,
    user_id: int,
    cursor: str | None,
    limit: int,
) -> tuple[list[int], str | None]:
    """特别关注浏览：PG keyset 直查用户标记为 is_special_followed 的订阅名下的视频。

    - 基表 Video ⨝ SubscriptionVideo ⨝ UserSubscription(is_special_followed=true)
    - 排序 publish_date DESC, id DESC（全序，与首页/Meili 浏览一致）
    - fan-out 去重：同一 video 可能被多个特别关注订阅关联，取最新的 publish_date 作为排序键
    - 只返回 publish_date <= now 的视频（与首页"全部"语义一致，排除未来视频）
    - cursor 编码 (sort_ts, video_id)，首页 cursor=None
    """
    from domains.subscription.domain.junctions.user_subscription import UserSubscription

    base = (
        select(
            Video.id,
            Video.publish_date,
        )
        .select_from(Video)
        .join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
        .join(
            UserSubscription,
            and_(
                UserSubscription.subscription_id == SubscriptionVideo.subscription_id,
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                UserSubscription.is_special_followed.is_(True),
            ),
        )
        .where(
            Video.is_deleted.is_(False),
            Video.publish_date.is_not(None),
            Video.publish_date <= func.now(),
        )
        # fan-out 去重：同一 video 取一行（多个特别关注订阅关联不影响排序键）
        .group_by(Video.id, Video.publish_date)
        .order_by(Video.publish_date.desc(), Video.id.desc())
        .limit(limit + 1)  # 多取 1 条判断 has_more
    )
    if cursor:
        decoded = decode_cursor(cursor)
        if decoded is not None:
            cur_ts, cur_id = decoded
            cur_ts_dt = datetime.fromtimestamp(cur_ts)
            base = base.where(
                (Video.publish_date < cur_ts_dt)
                | and_(Video.publish_date == cur_ts_dt, Video.id < cur_id),
            )

    rows = session.execute(base).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    video_ids = [r.id for r in rows]
    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = encode_cursor(int(last.publish_date.timestamp()), last.id)
    return video_ids, next_cursor


def fetch_user_state_video_ids(
    session: Session,
    *,
    user_id: int,
    category: str,
    cursor: str | None,
    limit: int,
) -> tuple[list[int], str | None]:
    """read/liked/later 无 query 场景：PG keyset 分页直查 per-user 表。

    - read: video_history ORDER BY end_time DESC, id DESC
    - liked: video_interaction WHERE interaction_type=1 ORDER BY created_at DESC, id DESC
    - later: video_interaction WHERE interaction_type=3 ORDER BY created_at DESC, id DESC

    cursor 编码 (sort_ts, row_id)；首页 cursor=None。
    返回 (video_ids, next_cursor)；next_cursor=None 表示无更多。
    """
    cursor_decoded = decode_cursor(cursor) if cursor else None

    if category == 'read':
        # video_history 按 (end_time DESC, id DESC) keyset
        stmt = (
            select(VideoHistory.id, VideoHistory.video_id, VideoHistory.end_time)
            .where(VideoHistory.user_id == user_id)
            .order_by(VideoHistory.end_time.desc(), VideoHistory.id.desc())
            .limit(limit + 1)  # 多取 1 条判断 has_more
        )
        if cursor_decoded is not None:
            cur_ts, cur_id = cursor_decoded
            cur_ts_dt = datetime.fromtimestamp(cur_ts)
            stmt = stmt.where(
                (VideoHistory.end_time < cur_ts_dt)
                | and_(VideoHistory.end_time == cur_ts_dt, VideoHistory.id < cur_id),
            )
        rows = session.execute(stmt).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        video_ids = [r.video_id for r in rows]
        next_cursor = None
        if has_more and rows:
            last = rows[-1]
            next_cursor = encode_cursor(int(last.end_time.timestamp()), last.id)
        return video_ids, next_cursor

    # liked/later: video_interaction
    interaction_type = _CATEGORY_INTERACTION_TYPE.get(category)
    if interaction_type is None:
        return [], None

    stmt = (
        select(VideoInteraction.id, VideoInteraction.video_id, VideoInteraction.created_at)
        .where(
            VideoInteraction.user_id == user_id,
            VideoInteraction.interaction_type == interaction_type,
        )
        .order_by(VideoInteraction.created_at.desc(), VideoInteraction.id.desc())
        .limit(limit + 1)
    )
    if cursor_decoded is not None:
        cur_ts, cur_id = cursor_decoded
        cur_ts_dt = datetime.fromtimestamp(cur_ts)
        stmt = stmt.where(
            (VideoInteraction.created_at < cur_ts_dt)
            | and_(VideoInteraction.created_at == cur_ts_dt, VideoInteraction.id < cur_id),
        )
    rows = session.execute(stmt).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    video_ids = [r.video_id for r in rows]
    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = encode_cursor(int(last.created_at.timestamp()), last.id)
    return video_ids, next_cursor


def fetch_user_state_id_set(
    session: Session,
    *,
    user_id: int,
    category: str,
    limit: int = 5000,
) -> list[int]:
    """read/liked/later 有 query 场景：取该用户该 category 的 video_id 集合（供 Meili filter）。

    buffer 策略：按交互时间倒序取最近 limit 个（默认 5000），覆盖绝大多数用户。
    超过 limit 的旧记录不在搜索范围（可接受：用户极少搜索超旧的已读/喜欢视频）。
    """
    if category == 'read':
        stmt = (
            select(VideoHistory.video_id)
            .where(VideoHistory.user_id == user_id)
            .order_by(VideoHistory.end_time.desc())
            .limit(limit)
        )
    else:
        interaction_type = _CATEGORY_INTERACTION_TYPE.get(category)
        if interaction_type is None:
            return []
        stmt = (
            select(VideoInteraction.video_id)
            .where(
                VideoInteraction.user_id == user_id,
                VideoInteraction.interaction_type == interaction_type,
            )
            .order_by(VideoInteraction.created_at.desc())
            .limit(limit)
        )
    return [r[0] for r in session.execute(stmt).all()]


def fetch_special_follow_id_set(
    session: Session,
    *,
    user_id: int,
    limit: int = 5000,
) -> list[int]:
    """特别关注有 query 场景：取该用户标记为 is_special_followed 订阅名下的 video_id 集合（供 Meili filter）。

    buffer 策略：按 publish_date 倒序取最近 limit 个（默认 5000）。超过 limit 的旧视频
    不在搜索范围（可接受：用户极少搜索超旧的特别关注视频）。
    """
    from domains.subscription.domain.junctions.user_subscription import UserSubscription

    stmt = (
        select(Video.id)
        .select_from(Video)
        .join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
        .join(
            UserSubscription,
            and_(
                UserSubscription.subscription_id == SubscriptionVideo.subscription_id,
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                UserSubscription.is_special_followed.is_(True),
            ),
        )
        .where(
            Video.is_deleted.is_(False),
            Video.publish_date.is_not(None),
            Video.publish_date <= func.now(),
        )
        # fan-out 去重
        .group_by(Video.id)
        .order_by(Video.publish_date.desc())
        .limit(limit)
    )
    return [r[0] for r in session.execute(stmt).all()]


def recall_offset_ids(
    *,
    query: str,
    domains: list[str] | None,
    time_range: str,
    duration: str,
    filter_ids: list[int] | None = None,
    limit: int = 5000,
    category: str = 'all',
) -> list[int]:
    """搜索场景 Meili 召回（OFFSET 分页用）。失败抛出由调用方处理。

    filter_ids 用于 read/liked/later 反向交集（PG 提供 per-user id 集合）。
    category='preview' 时放行未来视频；其余 category 一律排除未发布视频。
    """
    from domains.video.application.services.search.meili_indexer import get_meili_video_indexer
    return get_meili_video_indexer().recall(
        query,
        domains=domains,
        time_range=time_range,
        duration=duration,
        filter_ids=filter_ids,
        limit=limit,
        category=category,
    )
