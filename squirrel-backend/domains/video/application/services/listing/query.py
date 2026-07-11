from datetime import datetime

from sqlalchemy import and_, false, func, not_, or_, select
from sqlalchemy.orm import Session

from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.video.application.services.listing.query_filters import (
    build_active_subscriptions_query,
    feed_category_predicate,
)
from domains.video.application.services.moderation.nsfw_policy import (
    resolve_effective_nsfw_filter as _default_resolve_effective_nsfw_filter,
)
from domains.video.application.services.search.meili_indexer import (
    _CURSOR_KEY_CREATED,
    _CURSOR_KEY_HISTORY,
    _CURSOR_KEY_INTERACTION,
    _CURSOR_KEY_PUBLISH,
    decode_cursor_for_key,
    encode_cursor,
)
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.video.domain.junctions.video_creator import VideoCreator
from domains.video.domain.models.video import Video
from domains.video.domain.models.video_history import VideoHistory
from domains.video.domain.models.video_interaction import VideoInteraction
from infrastructure.site_catalog.catalog import SiteCatalog

# read/liked/later 的 interaction_type 映射
_CATEGORY_INTERACTION_TYPE: dict[str, int] = {
    'liked': 1,
    'later': 3,
}


class VideoListQueryService:
    def __init__(self, resolve_effective_nsfw_filter=None):
        resolve_nsfw_filter = resolve_effective_nsfw_filter or _default_resolve_effective_nsfw_filter
        self._resolve_effective_nsfw_filter = resolve_nsfw_filter
        self._build_active_subscriptions_query = lambda **kwargs: build_active_subscriptions_query(
            **kwargs,
            resolve_effective_nsfw_filter_func=resolve_nsfw_filter,
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
        """对 Meili 召回的 video_id 集合做 PG 权限 + category 过滤,保持召回顺序返回。

        PG 负责:
        - 权限(订阅/nsfw/special)走 active_subscriptions join
        - category(read/unread/liked/later/preview)走 feed_category_predicate EXISTS
        - content_type 走 active_subscriptions.c.subscription_type
        返回值按 recalled_ids 原始顺序去重(Meili 的排序即最终顺序)。

        注意:read/liked/later 场景下 category 过滤由上游 fetch_user_state_* 保证,
        此处传 category='all' 即可(避免重复 EXISTS);unread 场景仍需 NOT EXISTS。
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
            # read/liked/later 的 category 语义已由上游 per-user 表保证,这里不再 EXISTS
            # all/preview 不需要 category 过滤;unread 需要 NOT EXISTS
            query_stmt = query_stmt.where(
                feed_category_predicate(
                    user_id,
                    category,
                    video_id_column=Video.id,
                    publish_date_column=Video.publish_date,
                )
            )

        # fan-out 去重(同一 video 多个订阅会多行),取 set
        matched = {row[0] for row in session.execute(query_stmt).all()}

        # 按召回顺序返回(Meili 的排序即最终顺序)
        return [vid for vid in recalled_ids if vid in matched]

    def filter_user_state_ids(
        self,
        session: Session,
        *,
        recalled_ids: list[int],
        user_id: int,
        show_nsfw: bool,
        subscription_id: int | None,
        nsfw: str,
        domains: list[str] | None,
        content_type: str,
        special: str,
    ) -> list[int]:
        """Filter read/liked/later ids by video existence and visibility rules.

        read/liked/later are user-owned state lists. They must not disappear just
        because a video is no longer attached to an active subscription, has no
        subscription link, or has a missing publish_date. Sensitive-content
        visibility still applies globally.
        """
        if not recalled_ids:
            return []

        query_stmt = select(Video.id).where(
            Video.is_deleted.is_(False),
            Video.id.in_(recalled_ids),
        )
        if domains:
            normalized_domains = [domain.strip().lower() for domain in domains if domain and domain.strip()]
            if normalized_domains:
                query_stmt = query_stmt.where(func.lower(Video.domain).in_(normalized_domains))

        effective_nsfw = self._resolve_effective_nsfw_filter(nsfw, show_nsfw)
        needs_subscription_dimension_filter = (
            subscription_id is not None
            or content_type != 'all'
            or special != 'all'
        )
        if needs_subscription_dimension_filter:
            active_subscriptions = self._build_active_subscriptions_query(
                user_id=user_id,
                subscription_id=subscription_id,
                nsfw=nsfw,
                show_nsfw=show_nsfw,
                special=special,
            )
            query_stmt = (
                query_stmt.join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
                .join(active_subscriptions, active_subscriptions.c.subscription_id == SubscriptionVideo.subscription_id)
            )
            if content_type != 'all':
                query_stmt = query_stmt.where(active_subscriptions.c.subscription_type == content_type)
        elif effective_nsfw == 'blocked':
            return []
        elif effective_nsfw in {'yes', 'no'}:
            is_sensitive = self._user_state_sensitive_predicate(user_id=user_id)
            query_stmt = query_stmt.where(is_sensitive if effective_nsfw == 'yes' else not_(is_sensitive))

        matched = {row[0] for row in session.execute(query_stmt).all()}
        return [vid for vid in recalled_ids if vid in matched]

    @staticmethod
    def _user_state_sensitive_predicate(*, user_id: int):
        nsfw_subscription_video_ids = (
            select(SubscriptionVideo.video_id)
            .select_from(SubscriptionVideo)
            .join(
                UserSubscription,
                and_(
                    UserSubscription.subscription_id == SubscriptionVideo.subscription_id,
                    UserSubscription.user_id == user_id,
                    UserSubscription.is_deleted.is_(False),
                    UserSubscription.is_nsfw.is_(True),
                ),
            )
            .join(
                Subscription,
                and_(
                    Subscription.id == SubscriptionVideo.subscription_id,
                    Subscription.is_deleted.is_(False),
                ),
            )
        )
        nsfw_domains = _nsfw_site_domains()
        domain_is_nsfw = (
            and_(Video.domain.is_not(None), func.lower(Video.domain).in_(nsfw_domains))
            if nsfw_domains
            else false()
        )
        return or_(Video.id.in_(nsfw_subscription_video_ids), domain_is_nsfw)


def _nsfw_site_domains() -> list[str]:
    domains: list[str] = []
    for info in SiteCatalog._get_effective_catalog().values():
        if not bool((info.get('metadata') or {}).get('nsfw', False)):
            continue
        domains.extend(str(domain or '').strip().lower() for domain in info.get('domains', []) if domain)
    return list(dict.fromkeys(domains))


video_list_query_service = VideoListQueryService()

# 模块级便捷函数
filter_recalled_ids = video_list_query_service.filter_recalled_ids
filter_user_state_ids = video_list_query_service.filter_user_state_ids


def fetch_special_follow_video_ids(
    session: Session,
    *,
    user_id: int,
    cursor: str | None,
    limit: int,
    sort_by: str = 'publish_date',
) -> tuple[list[int], str | None]:
    """特别关注浏览:PG keyset 直查用户标记为 is_special_followed 的订阅名下的视频。

    - 基表 Video ⨝ SubscriptionVideo ⨝ UserSubscription(is_special_followed=true)
    - 排序按 sort_by:publish_date(上传日期)或 created_at(抓取日期)DESC,id DESC 作次级键(全序)
    - fan-out 去重:同一 video 可能被多个特别关注订阅关联,group_by 取一行
    - 只返回 publish_date <= now 的视频(与首页"全部"语义一致,排除未来视频;
      此过滤与排序键无关,始终用 publish_date)
    - cursor 编码 (key, sort_ts, video_id),首页 cursor=None;key 与 sort_by 必须匹配,
      不匹配(老游标/串用)→ decode 返回 None → 等价回首页
    """
    from domains.subscription.domain.junctions.user_subscription import UserSubscription

    # 按 sort_by 选排序键/游标键;默认 publish_date
    use_created = sort_by == 'created_at'
    sort_col = Video.created_at if use_created else Video.publish_date
    expected_key = _CURSOR_KEY_CREATED if use_created else _CURSOR_KEY_PUBLISH

    base = (
        select(
            Video.id,
            Video.publish_date,
            Video.created_at,
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
        # fan-out 去重:同一 video 取一行(多个特别关注订阅关联不影响排序键)
        .group_by(Video.id, Video.publish_date, Video.created_at)
        .order_by(sort_col.desc(), Video.id.desc())
        .limit(limit + 1)  # 多取 1 条判断 has_more
    )
    decoded = decode_cursor_for_key(cursor, expected_key)
    if decoded is not None:
        cur_ts, cur_id = decoded
        cur_ts_dt = datetime.fromtimestamp(cur_ts)
        base = base.where(
            (sort_col < cur_ts_dt) | and_(sort_col == cur_ts_dt, Video.id < cur_id),
        )

    rows = session.execute(base).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    video_ids = [r.id for r in rows]
    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        last_ts = last.created_at if use_created else last.publish_date
        next_cursor = encode_cursor(expected_key, int(last_ts.timestamp()), last.id)
    return video_ids, next_cursor


def fetch_subscription_video_ids(
    session: Session,
    *,
    user_id: int,
    subscription_id: int,
    cursor: str | None,
    limit: int,
    category: str = 'all',
    sort_by: str = 'publish_date',
) -> tuple[list[int], str | None]:
    """指定订阅浏览:PG keyset 直查该订阅名下的视频。

    与 fetch_special_follow_video_ids 同构,但用途不同——后者服务首页"特别关注"区块
    (is_special_followed=true),本函数服务频道详情页"本地"列表(指定 subscription_id)。

    为什么不走 Meili 全局召回:Meili recall_page 按 publish_ts:desc 全局召回最新 N 条
    (最多 _MAX_RECALL_ROUNDSx(page_size*2)),再用 subscription_id 在 PG 侧过滤。
    指定订阅的视频一旦比其他订阅旧,或未被索引/重建,就永远进不了召回窗口 →
    频道详情页即使解析了上百条视频,"本地"列表也只显示寥寥几条,且 Meili 游标到底后
    next_cursor=None 导致前端无限滚动立刻停止。改走 PG keyset 直查彻底规避此问题。

    - 基表 Video ⨝ SubscriptionVideo ⨝ UserSubscription(归属校验,防越权)
    - 排序按 sort_by:publish_date(上传日期)或 created_at(抓取日期)DESC,id DESC 作次级键(全序)
    - fan-out 去重:同一 video 可能被多个订阅关联,group_by 取一行
    - publish_date 边界:category='preview' 取未来视频(publish_date > now);
      其余取已发布(publish_date <= now AND IS NOT NULL)。此过滤是发布语义,
      与排序键无关,始终用 publish_date
    - read/unread/liked/later 的 EXISTS 语义不在 fetch 阶段过滤——交给下游 filter_recalled_ids
      (调用方 _list_subscription_browse 仅会被 category ∈ {all, unread, preview} 触发:
      read/liked/later 在 _list_browse_keyset 开头即分流到 user-state 路径)
    - has_more 看 PG keyset 是否还有更多(与 user-state/special-follow 一致),
      即使下游 filter 后不足一页也允许翻页
    - cursor 编码 (key, sort_ts, video_id),首页 cursor=None
    """
    from domains.subscription.domain.junctions.user_subscription import UserSubscription

    # 按 sort_by 选排序键/游标键;默认 publish_date
    use_created = sort_by == 'created_at'
    sort_col = Video.created_at if use_created else Video.publish_date
    expected_key = _CURSOR_KEY_CREATED if use_created else _CURSOR_KEY_PUBLISH

    base = (
        select(
            Video.id,
            Video.publish_date,
            Video.created_at,
        )
        .select_from(Video)
        .join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
        .join(
            UserSubscription,
            and_(
                UserSubscription.subscription_id == SubscriptionVideo.subscription_id,
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                UserSubscription.subscription_id == subscription_id,
            ),
        )
        .where(Video.is_deleted.is_(False))
    )
    if category == 'preview':
        # 预告 tab:只看未来视频(与 Meili _build_recall_filter 的 preview 分支一致)
        base = base.where(Video.publish_date > func.now())
    else:
        base = base.where(
            Video.publish_date.is_not(None),
            Video.publish_date <= func.now(),
        )
    # fan-out 去重:同一 video 多个订阅关联只取一行
    base = (
        base.group_by(Video.id, Video.publish_date, Video.created_at)
        .order_by(sort_col.desc(), Video.id.desc())
        .limit(limit + 1)  # 多取 1 条判断 has_more
    )
    decoded = decode_cursor_for_key(cursor, expected_key)
    if decoded is not None:
        cur_ts, cur_id = decoded
        cur_ts_dt = datetime.fromtimestamp(cur_ts)
        base = base.where(
            (sort_col < cur_ts_dt) | and_(sort_col == cur_ts_dt, Video.id < cur_id),
        )

    rows = session.execute(base).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    video_ids = [r.id for r in rows]
    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        last_ts = last.created_at if use_created else last.publish_date
        next_cursor = encode_cursor(expected_key, int(last_ts.timestamp()), last.id)
    return video_ids, next_cursor


def fetch_creator_video_ids(
    session: Session,
    *,
    creator_id: int,
    cursor: str | None,
    limit: int,
    category: str = 'all',
    sort_by: str = 'publish_date',
) -> tuple[list[int], str | None]:
    """指定创作者浏览:PG keyset 直查 video_creator 关联视频。

    与 fetch_subscription_video_ids 同构,但不 join UserSubscription——创作者页
    展示库内已关联视频,不要求当前用户订阅了对应频道。
    """
    use_created = sort_by == 'created_at'
    sort_col = Video.created_at if use_created else Video.publish_date
    expected_key = _CURSOR_KEY_CREATED if use_created else _CURSOR_KEY_PUBLISH

    base = (
        select(
            Video.id,
            Video.publish_date,
            Video.created_at,
        )
        .select_from(Video)
        .join(VideoCreator, VideoCreator.video_id == Video.id)
        .where(
            Video.is_deleted.is_(False),
            VideoCreator.creator_id == creator_id,
        )
    )
    if category == 'preview':
        base = base.where(Video.publish_date > func.now())
    else:
        base = base.where(
            Video.publish_date.is_not(None),
            Video.publish_date <= func.now(),
        )
    base = (
        base.group_by(Video.id, Video.publish_date, Video.created_at)
        .order_by(sort_col.desc(), Video.id.desc())
        .limit(limit + 1)
    )
    decoded = decode_cursor_for_key(cursor, expected_key)
    if decoded is not None:
        cur_ts, cur_id = decoded
        cur_ts_dt = datetime.fromtimestamp(cur_ts)
        base = base.where(
            (sort_col < cur_ts_dt) | and_(sort_col == cur_ts_dt, Video.id < cur_id),
        )

    rows = session.execute(base).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    video_ids = [r.id for r in rows]
    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        last_ts = last.created_at if use_created else last.publish_date
        next_cursor = encode_cursor(expected_key, int(last_ts.timestamp()), last.id)
    return video_ids, next_cursor


def fetch_user_state_video_ids(
    session: Session,
    *,
    user_id: int,
    category: str,
    cursor: str | None,
    limit: int,
) -> tuple[list[int], str | None]:
    """read/liked/later 无 query 场景:PG keyset 分页直查 per-user 表。

    - read: video_history ORDER BY end_time DESC, id DESC
    - liked: video_interaction WHERE interaction_type=1 ORDER BY created_at DESC, id DESC
    - later: video_interaction WHERE interaction_type=3 ORDER BY created_at DESC, id DESC

    cursor 编码 (key, sort_ts, row_id),首页 cursor=None。
    key 用独立命名空间(h=history/i=interaction),与视频排序键(p/c)隔离,
    互不串用;不匹配或老游标 → decode 返回 None → 等价回首页。
    返回 (video_ids, next_cursor);next_cursor=None 表示无更多。
    """
    if category == 'read':
        # video_history 按 (end_time DESC, id DESC) keyset
        cursor_decoded = decode_cursor_for_key(cursor, _CURSOR_KEY_HISTORY)
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
            next_cursor = encode_cursor(_CURSOR_KEY_HISTORY, int(last.end_time.timestamp()), last.id)
        return video_ids, next_cursor

    # liked/later: video_interaction
    interaction_type = _CATEGORY_INTERACTION_TYPE.get(category)
    if interaction_type is None:
        return [], None

    cursor_decoded = decode_cursor_for_key(cursor, _CURSOR_KEY_INTERACTION)
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
        next_cursor = encode_cursor(_CURSOR_KEY_INTERACTION, int(last.created_at.timestamp()), last.id)
    return video_ids, next_cursor


def fetch_user_state_id_set(
    session: Session,
    *,
    user_id: int,
    category: str,
) -> list[int]:
    """read/liked/later 有 query 场景:取该用户该 category 的 video_id 集合(供 Meili filter)。

    这里不能截断。用户在 read/liked/later 分类里搜索时,语义是“在该用户全部状态集合内搜索”,
    固定取最近 N 条会让旧的已读/喜欢/稍后再看视频从搜索范围里消失,导致分类数量与实际状态不一致。
    """
    if category == 'read':
        stmt = (
            select(VideoHistory.video_id)
            .where(VideoHistory.user_id == user_id)
            .order_by(VideoHistory.end_time.desc())
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
        )
    return [r[0] for r in session.execute(stmt).all()]


def fetch_special_follow_id_set(
    session: Session,
    *,
    user_id: int,
    limit: int = 5000,
) -> list[int]:
    """特别关注有 query 场景:取该用户标记为 is_special_followed 订阅名下的 video_id 集合(供 Meili filter)。

    buffer 策略:按 publish_date 倒序取最近 limit 个(默认 5000)。超过 limit 的旧视频
    不在搜索范围(可接受:用户极少搜索超旧的特别关注视频)。
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
    """搜索场景 Meili 召回(OFFSET 分页用)。失败抛出由调用方处理。

    filter_ids 用于 read/liked/later 反向交集(PG 提供 per-user id 集合)。
    category='preview' 时放行未来视频;其余 category 一律排除未发布视频。
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
