from typing import Optional, List

from sqlalchemy import select, func, and_, exists, or_
from sqlalchemy.orm import aliased

from models.creator import Creator
from models.video import Video
from models.links import SubscriptionVideo, UserSubscription, VideoCreator
from models.subscription import Subscription
from models.video_history import VideoHistory
from models.video_interaction import VideoInteraction
from services.search_query import normalize_subscription_type_term, parse_search_query
from utils import url_helper


def _contains(column, term: str):
    return column.ilike(f'%{term}%')


def _video_match_clause(*, video_id_column, term: str):
    video_alias = aliased(Video)
    return exists(
        select(1)
        .select_from(video_alias)
        .where(
            video_alias.id == video_id_column,
            video_alias.is_deleted.is_(False),
            or_(
                _contains(video_alias.title, term),
                _contains(video_alias.description, term),
                _contains(video_alias.url, term),
                _contains(video_alias.domain, term),
            ),
        )
    )


def _subscription_match_clause(*, user_id: int, video_id_column=None, subscription_id_column=None, term: str):
    if subscription_id_column is not None:
        return exists(
            select(1)
            .select_from(Subscription)
            .join(
                UserSubscription,
                and_(
                    UserSubscription.subscription_id == Subscription.id,
                    UserSubscription.user_id == user_id,
                    UserSubscription.is_deleted.is_(False),
                ),
            )
            .where(
                Subscription.id == subscription_id_column,
                Subscription.is_deleted.is_(False),
                or_(
                    _contains(Subscription.name, term),
                    _contains(Subscription.url, term),
                    _contains(Subscription.description, term),
                ),
            )
        )

    return exists(
        select(1)
        .select_from(SubscriptionVideo)
        .join(Subscription, Subscription.id == SubscriptionVideo.subscription_id)
        .join(
            UserSubscription,
            and_(
                UserSubscription.subscription_id == Subscription.id,
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
            ),
        )
        .where(
            SubscriptionVideo.video_id == video_id_column,
            Subscription.is_deleted.is_(False),
            or_(
                _contains(Subscription.name, term),
                _contains(Subscription.url, term),
                _contains(Subscription.description, term),
            ),
        )
    )


def _subscription_type_clause(*, user_id: int, video_id_column=None, subscription_id_column=None, value: str):
    normalized_type = normalize_subscription_type_term(value)
    if not normalized_type:
        return None

    if subscription_id_column is not None:
        return exists(
            select(1)
            .select_from(Subscription)
            .join(
                UserSubscription,
                and_(
                    UserSubscription.subscription_id == Subscription.id,
                    UserSubscription.user_id == user_id,
                    UserSubscription.is_deleted.is_(False),
                ),
            )
            .where(
                Subscription.id == subscription_id_column,
                Subscription.is_deleted.is_(False),
                Subscription.type == normalized_type,
            )
        )

    return exists(
        select(1)
        .select_from(SubscriptionVideo)
        .join(Subscription, Subscription.id == SubscriptionVideo.subscription_id)
        .join(
            UserSubscription,
            and_(
                UserSubscription.subscription_id == Subscription.id,
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
            ),
        )
        .where(
            SubscriptionVideo.video_id == video_id_column,
            Subscription.is_deleted.is_(False),
            Subscription.type == normalized_type,
        )
    )


def _creator_match_clause(*, video_id_column, term: str):
    return exists(
        select(1)
        .select_from(VideoCreator)
        .join(Creator, Creator.id == VideoCreator.creator_id)
        .where(
            VideoCreator.video_id == video_id_column,
            Creator.is_deleted.is_(False),
            or_(
                _contains(Creator.name, term),
                _contains(Creator.url, term),
                _contains(Creator.description, term),
            ),
        )
    )


def build_video_search_clauses(*, user_id: int, query: Optional[str], video_id_column, subscription_id_column=None):
    parsed_query = parse_search_query(query)
    if not parsed_query.has_terms:
        return []

    clauses = []

    for term in parsed_query.text_terms:
        clauses.append(
            or_(
                _video_match_clause(video_id_column=video_id_column, term=term),
                _subscription_match_clause(
                    user_id=user_id,
                    video_id_column=video_id_column,
                    subscription_id_column=subscription_id_column,
                    term=term,
                ),
                _creator_match_clause(video_id_column=video_id_column, term=term),
            )
        )

    for term in parsed_query.get('title'):
        video_alias = aliased(Video)
        clauses.append(
            exists(
                select(1)
                .select_from(video_alias)
                .where(
                    video_alias.id == video_id_column,
                    video_alias.is_deleted.is_(False),
                    _contains(video_alias.title, term),
                )
            )
        )

    for term in parsed_query.get('url'):
        video_alias = aliased(Video)
        clauses.append(
            exists(
                select(1)
                .select_from(video_alias)
                .where(
                    video_alias.id == video_id_column,
                    video_alias.is_deleted.is_(False),
                    _contains(video_alias.url, term),
                )
            )
        )

    for term in parsed_query.get('domain'):
        video_alias = aliased(Video)
        clauses.append(
            exists(
                select(1)
                .select_from(video_alias)
                .where(
                    video_alias.id == video_id_column,
                    video_alias.is_deleted.is_(False),
                    _contains(video_alias.domain, term),
                )
            )
        )

    for term in parsed_query.get('description'):
        clauses.append(
            or_(
                _video_match_clause(video_id_column=video_id_column, term=term),
                _subscription_match_clause(
                    user_id=user_id,
                    video_id_column=video_id_column,
                    subscription_id_column=subscription_id_column,
                    term=term,
                ),
                _creator_match_clause(video_id_column=video_id_column, term=term),
            )
        )

    for term in parsed_query.get('subscription'):
        clauses.append(
            _subscription_match_clause(
                user_id=user_id,
                video_id_column=video_id_column,
                subscription_id_column=subscription_id_column,
                term=term,
            )
        )

    for term in parsed_query.get('creator'):
        clauses.append(_creator_match_clause(video_id_column=video_id_column, term=term))

    for term in parsed_query.get('type'):
        type_clause = _subscription_type_clause(
            user_id=user_id,
            video_id_column=video_id_column,
            subscription_id_column=subscription_id_column,
            value=term,
        )
        if type_clause is not None:
            clauses.append(type_clause)

    return clauses


def _build_base_video_conditions(
        user_id: int,
        show_nsfw: bool,
        subscription_id: Optional[int] = None,
        query: Optional[str] = None,
        nsfw: str = 'all',
        domains: Optional[List[str]] = None
):
    conditions = [
        Video.is_deleted == False,
        UserSubscription.is_deleted == False,
        Subscription.is_deleted == False,
        UserSubscription.user_id == user_id
    ]

    if subscription_id:
        conditions.append(SubscriptionVideo.subscription_id == subscription_id)

    if nsfw == 'yes':
        conditions.append(UserSubscription.is_nsfw == True)
    elif nsfw == 'no':
        conditions.append(UserSubscription.is_nsfw == False)
    else:
        if not show_nsfw:
            conditions.append(UserSubscription.is_nsfw == False)

    conditions.extend(build_video_search_clauses(
        user_id=user_id,
        query=query,
        video_id_column=Video.id,
    ))

    if domains:
        normalized_domains = [
            d for d in {url_helper.normalize_domain(domain) for domain in domains if domain} if d
        ]
        if normalized_domains:
            conditions.append(Video.domain.in_(normalized_domains))

    return conditions


def build_base_video_query(
        user_id: int,
        show_nsfw: bool,
        subscription_id: Optional[int] = None,
        query: Optional[str] = None,
        nsfw: str = 'all',
        domains: Optional[List[str]] = None
):
    """构建基础视频查询，以 Video 为主表。"""
    base_query = (
        select(Video, SubscriptionVideo.subscription_id.label('subscription_id'))
        .select_from(Video)
        .join(SubscriptionVideo, Video.id == SubscriptionVideo.video_id)
        .join(UserSubscription, SubscriptionVideo.subscription_id == UserSubscription.subscription_id)
        .join(Subscription, UserSubscription.subscription_id == Subscription.id)
    )

    return base_query.where(
        and_(*_build_base_video_conditions(user_id, show_nsfw, subscription_id, query, nsfw, domains))
    )


def build_video_count_source_query(
        user_id: int,
        show_nsfw: bool,
        subscription_id: Optional[int] = None,
        query: Optional[str] = None,
        nsfw: str = 'all',
        domains: Optional[List[str]] = None
):
    user_subscriptions = (
        select(UserSubscription.subscription_id.label('subscription_id'))
        .select_from(UserSubscription)
        .join(Subscription, Subscription.id == UserSubscription.subscription_id)
        .where(
            and_(
                UserSubscription.is_deleted == False,
                Subscription.is_deleted == False,
                UserSubscription.user_id == user_id
            )
        )
    )

    if subscription_id:
        user_subscriptions = user_subscriptions.where(UserSubscription.subscription_id == subscription_id)

    if nsfw == 'yes':
        user_subscriptions = user_subscriptions.where(UserSubscription.is_nsfw == True)
    elif nsfw == 'no':
        user_subscriptions = user_subscriptions.where(UserSubscription.is_nsfw == False)
    elif not show_nsfw:
        user_subscriptions = user_subscriptions.where(UserSubscription.is_nsfw == False)

    user_subscriptions = user_subscriptions.cte('user_subscriptions')

    count_source = (
        select(
            Video.id.label('video_id'),
            Video.publish_date.label('publish_date')
        )
        .select_from(user_subscriptions)
        .join(SubscriptionVideo, SubscriptionVideo.subscription_id == user_subscriptions.c.subscription_id)
        .join(Video, Video.id == SubscriptionVideo.video_id)
        .where(Video.is_deleted == False)
    )

    search_clauses = build_video_search_clauses(
        user_id=user_id,
        query=query,
        video_id_column=Video.id,
    )
    if search_clauses:
        count_source = count_source.where(*search_clauses)

    if domains:
        normalized_domains = [
            d for d in {url_helper.normalize_domain(domain) for domain in domains if domain} if d
        ]
        if normalized_domains:
            count_source = count_source.where(Video.domain.in_(normalized_domains))

    return count_source.distinct()


def category_predicate(user_id: int, category: Optional[str]):
    """返回分类筛选条件，复用在列表/计数/随机。"""
    published = Video.publish_date <= func.now()

    if category == 'preview':
        return Video.publish_date > func.now()
    if category == 'read':
        return and_(
            published,
            exists(
                select(1).where(
                    and_(
                        VideoHistory.user_id == user_id,
                        VideoHistory.video_id == Video.id
                    )
                )
            )
        )
    if category == 'unread':
        return and_(
            published,
            ~exists(
                select(1).where(
                    and_(
                        VideoHistory.user_id == user_id,
                        VideoHistory.video_id == Video.id
                    )
                )
            )
        )
    if category == 'liked':
        return and_(
            published,
            exists(
                select(1).where(
                    and_(
                        VideoInteraction.user_id == user_id,
                        VideoInteraction.video_id == Video.id,
                        VideoInteraction.interaction_type == 1
                    )
                )
            )
        )
    if category == 'later':
        return and_(
            published,
            exists(
                select(1).where(
                    and_(
                        VideoInteraction.user_id == user_id,
                        VideoInteraction.video_id == Video.id,
                        VideoInteraction.interaction_type == 3
                    )
                )
            )
        )

    return published


def resolve_sort_column(sort_by: str):
    if sort_by == 'created_at':
        return Video.created_at
    return Video.publish_date
