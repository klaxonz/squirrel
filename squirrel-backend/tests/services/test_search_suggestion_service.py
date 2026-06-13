from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from shared_kernel.domain.base import Base
from domains.video.domain.junctions.subscription_video import SubscriptionVideo, UserSubscription, VideoCreator
from domains.subscription.domain.models.subscription import ContentType, Subscription
from domains.user.domain.models.user_video_feed import UserVideoFeed
from domains.user.application.services.search.suggestion_service import SearchSuggestionService
from domains.video.domain.models.creator import Creator
from domains.video.domain.models.video import Video
from domains.video.domain.models.video_history import VideoHistory


@pytest.fixture
def svc(session_factory):
    return SearchSuggestionService(
        session_factory=session_factory,
        get_user_config=lambda _user_id: {'showNsfw': False},
    )


def _seed_visible_content(engine):
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            Subscription(
                id=1,
                type=ContentType.CHANNEL,
                name='黑神话研究所',
                url='https://space.bilibili.com/1',
                is_deleted=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 3),
            ),
        )
        session.add(
            UserSubscription(
                id=1,
                user_id=7,
                subscription_id=1,
                is_deleted=False,
                is_nsfw=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 3),
            ),
        )
        session.add(
            Video(
                id=1,
                title='黑神话悟空 终极预告',
                url='https://www.bilibili.com/video/BV1xx',
                domain='bilibili.com',
                is_deleted=False,
                created_at=datetime(2024, 1, 2),
                publish_date=datetime(2024, 1, 2),
            ),
        )
        session.add(SubscriptionVideo(subscription_id=1, video_id=1))
        session.add(
            UserVideoFeed(
                id=1,
                user_id=7,
                subscription_id=1,
                video_id=1,
                publish_date=datetime(2024, 1, 2),
                video_created_at=datetime(2024, 1, 2),
                domain='bilibili.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 2),
                updated_at=datetime(2024, 1, 2),
            ),
        )
        session.add(
            Creator(
                id=1,
                name='黑神话官方',
                url='https://space.bilibili.com/100',
                is_deleted=False,
                created_at=datetime(2024, 1, 2),
                updated_at=datetime(2024, 1, 2),
            ),
        )
        session.add(VideoCreator(video_id=1, creator_id=1))
        session.add(
            VideoHistory(
                id=1,
                user_id=7,
                video_id=1,
                start_time=datetime(2024, 1, 2, 12, 0, 0),
                end_time=datetime(2024, 1, 2, 12, 30, 0),
                duration=120,
                watch_duration=120,
                last_position=118,
                created_at=datetime(2024, 1, 2, 12, 0, 0),
                updated_at=datetime(2024, 1, 2, 12, 30, 0),
            ),
        )
        session.commit()


def _seed_nsfw_content(engine):
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            Subscription(
                id=2,
                type=ContentType.CHANNEL,
                name='秘密频道',
                url='https://secret.example.com/channel',
                is_deleted=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
        )
        session.add(
            UserSubscription(
                id=2,
                user_id=7,
                subscription_id=2,
                is_deleted=False,
                is_nsfw=True,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
        )
        session.add(
            Video(
                id=2,
                title='秘密影片预告',
                url='https://secret.example.com/video/1',
                domain='secret.example.com',
                is_deleted=False,
                created_at=datetime(2024, 1, 4),
                publish_date=datetime(2024, 1, 4),
            ),
        )
        session.add(SubscriptionVideo(subscription_id=2, video_id=2))
        session.add(
            UserVideoFeed(
                id=2,
                user_id=7,
                subscription_id=2,
                video_id=2,
                publish_date=datetime(2024, 1, 4),
                video_created_at=datetime(2024, 1, 4),
                domain='secret.example.com',
                is_nsfw=True,
                created_at=datetime(2024, 1, 4),
                updated_at=datetime(2024, 1, 4),
            ),
        )
        session.commit()


def test_list_search_suggestions_prioritizes_scope_specific_sources(engine, svc):
    Base.metadata.create_all(
        engine,
        tables=[
            Video.__table__,
            Subscription.__table__,
            SubscriptionVideo.__table__,
            UserSubscription.__table__,
            UserVideoFeed.__table__,
            VideoHistory.__table__,
            Creator.__table__,
            VideoCreator.__table__,
        ],
    )
    _seed_visible_content(engine)

    items = svc.list_search_suggestions(7, query='黑神话', scope='history', limit=5)

    assert items
    assert items[0]['type'] == 'history'
    assert items[0]['value'] == '黑神话悟空 终极预告'
    assert any(item['type'] == 'subscription' for item in items)
    assert any(item['type'] == 'creator' for item in items)


def test_list_search_suggestions_hides_nsfw_items_when_user_disabled(engine, svc):
    Base.metadata.create_all(
        engine,
        tables=[
            Video.__table__,
            Subscription.__table__,
            SubscriptionVideo.__table__,
            UserSubscription.__table__,
            UserVideoFeed.__table__,
            VideoHistory.__table__,
            Creator.__table__,
            VideoCreator.__table__,
        ],
    )
    _seed_visible_content(engine)
    _seed_nsfw_content(engine)

    items = svc.list_search_suggestions(7, query='秘密', scope='home', limit=5)

    assert items == []


def test_home_scope_uses_user_feed_video_suggestions(engine, svc):
    Base.metadata.create_all(
        engine,
        tables=[
            Video.__table__,
            Subscription.__table__,
            SubscriptionVideo.__table__,
            UserSubscription.__table__,
            UserVideoFeed.__table__,
            VideoHistory.__table__,
            Creator.__table__,
            VideoCreator.__table__,
        ],
    )
    _seed_visible_content(engine)

    items = svc.list_search_suggestions(7, query='终极', scope='home', limit=5)

    assert items
    assert items[0]['type'] == 'video'
    assert items[0]['value'] == '黑神话悟空 终极预告'


def test_invalidate_users_for_subscription_clears_user_caches(engine, svc):
    Base.metadata.create_all(
        engine,
        tables=[
            Subscription.__table__,
            UserSubscription.__table__,
        ],
    )
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            Subscription(
                id=3,
                type=ContentType.CHANNEL,
                name='缓存频道',
                url='https://example.com/channel',
                is_deleted=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
        )
        session.add(
            UserSubscription(
                id=3,
                user_id=7,
                subscription_id=3,
                is_deleted=False,
                is_nsfw=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
        )
        session.commit()

    svc._suggestion_pool_cache[(7, 'home', 'no')] = (999999.0, [{'type': 'video', 'value': 'old'}])
    svc._suggestion_result_cache[(7, 'home', 'no', 'old', 8)] = (999999.0, [{'type': 'video', 'value': 'old'}])
    svc._suggestion_pool_cache[(8, 'home', 'no')] = (999999.0, [{'type': 'video', 'value': 'keep'}])

    svc.invalidate_users_for_subscription(3)

    assert (7, 'home', 'no') not in svc._suggestion_pool_cache
    assert (7, 'home', 'no', 'old', 8) not in svc._suggestion_result_cache
    assert (8, 'home', 'no') in svc._suggestion_pool_cache
