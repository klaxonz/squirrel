"""Tests for SubscriptionListService.get_subscription_detail.

Covers the ORM query (formerly a raw-SQL string in sql/subscription_sql.py):
subscription columns + per-subscription video count + incremental sync-state
projection + synthetic is_nsfw/is_special_followed columns fed into SubscriptionDto.
"""

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from domains.subscription.application.services.core.listing.service import SubscriptionListService
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.video.domain.models.video import Video
from domains.video.domain.models.video_history import VideoHistory
from infrastructure.database.base import Base


def _make_service():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            Video.__table__,
            Subscription.__table__,
            SubscriptionVideo.__table__,
            VideoHistory.__table__,
            UserSubscription.__table__,
            SubscriptionSyncState.__table__,
        ],
    )
    return SubscriptionListService(
        session_factory=lambda: Session(engine, expire_on_commit=False),
        get_user_config=lambda _user_id: {'showNsfw': False},
    )


def test_get_subscription_detail_returns_dto_with_sync_state_and_counts():
    svc = _make_service()
    with svc.session_factory() as session:
        session.add_all(
            [
                Subscription(id=1, type='CHANNEL', name='demo', url='https://www.youtube.com/c/demo', total_videos=3),
                SubscriptionVideo(subscription_id=1, video_id=10),
                SubscriptionSyncState(
                    subscription_id=1,
                    site='youtube.com',
                    sync_mode='incremental',
                    sync_status='success',
                    pending_video_count=2,
                ),
            ]
        )
        session.commit()

    dto = svc.get_subscription_detail(1)

    assert dto is not None
    assert dto.id == 1
    assert dto.name == 'demo'
    # total_videos = max(stored total_videos=3, actual video_count=1)
    assert dto.total_videos == 3
    assert dto.total_extract == 1
    assert dto.sync_status == 'success'
    assert dto.pending_video_count == 2


def test_get_subscription_detail_returns_none_when_missing():
    svc = _make_service()
    assert svc.get_subscription_detail(999) is None


def test_get_subscription_detail_defaults_sync_state_when_absent():
    """No subscription_sync_state row -> sync_status defaults to 'idle', counts to 0."""
    svc = _make_service()
    with svc.session_factory() as session:
        session.add(Subscription(id=2, type='CHANNEL', name='nosync', url='https://x.com', total_videos=5))
        session.commit()

    dto = svc.get_subscription_detail(2)

    assert dto is not None
    assert dto.id == 2
    assert dto.sync_status == 'idle'
    assert dto.pending_video_count == 0


def test_list_subscriptions_hides_nsfw_channels_when_user_setting_is_disabled():
    svc = SubscriptionListService(
        session_factory=_make_service().session_factory,
        get_user_config=lambda _user_id: {'showNsfw': False},
    )
    with svc.session_factory() as session:
        session.add_all(
            [
                Subscription(
                    id=10,
                    type='CHANNEL',
                    name='PH model',
                    url='https://www.youtube.com/model/demo',
                    total_videos=8,
                ),
                UserSubscription(
                    user_id=7,
                    subscription_id=10,
                    is_deleted=False,
                    is_nsfw=True,
                ),
            ]
        )
        session.commit()

    subscriptions, total = svc.list_subscriptions(
        user_id=7,
        query=None,
        type=None,
        nsfw='all',
        page=1,
        page_size=20,
        domains=['youtube.com'],
    )

    assert total == 0
    assert subscriptions == []


def test_list_subscriptions_includes_nsfw_channels_when_user_setting_is_enabled():
    svc = SubscriptionListService(
        session_factory=_make_service().session_factory,
        get_user_config=lambda _user_id: {'showNsfw': True},
    )
    with svc.session_factory() as session:
        session.add_all(
            [
                Subscription(
                    id=13,
                    type='CHANNEL',
                    name='PH model',
                    url='https://www.youtube.com/model/demo',
                    total_videos=8,
                ),
                UserSubscription(
                    user_id=7,
                    subscription_id=13,
                    is_deleted=False,
                    is_nsfw=True,
                ),
            ]
        )
        session.commit()

    subscriptions, total = svc.list_subscriptions(
        user_id=7,
        query=None,
        type=None,
        nsfw='all',
        page=1,
        page_size=20,
        domains=['youtube.com'],
    )

    assert total == 1
    assert [subscription['name'] for subscription in subscriptions] == ['PH model']
    assert subscriptions[0]['is_nsfw'] is True


def test_list_subscriptions_respects_explicit_nsfw_no_filter():
    svc = SubscriptionListService(
        session_factory=_make_service().session_factory,
        get_user_config=lambda _user_id: {'showNsfw': True},
    )
    with svc.session_factory() as session:
        session.add_all(
            [
                Subscription(
                    id=11,
                    type='CHANNEL',
                    name='Safe channel',
                    url='https://www.youtube.com/@safe',
                    total_videos=2,
                ),
                Subscription(
                    id=12,
                    type='CHANNEL',
                    name='PH model',
                    url='https://www.youtube.com/model/demo',
                    total_videos=8,
                ),
                UserSubscription(
                    user_id=7,
                    subscription_id=11,
                    is_deleted=False,
                    is_nsfw=False,
                ),
                UserSubscription(
                    user_id=7,
                    subscription_id=12,
                    is_deleted=False,
                    is_nsfw=True,
                ),
            ]
        )
        session.commit()

    subscriptions, total = svc.list_subscriptions(
        user_id=7,
        query=None,
        type=None,
        nsfw='no',
        page=1,
        page_size=20,
    )

    assert total == 1
    assert [subscription['name'] for subscription in subscriptions] == ['Safe channel']


def test_list_subscriptions_disables_pagination_unique(monkeypatch):
    svc = SubscriptionListService(
        session_factory=lambda: None,
        get_user_config=lambda _user_id: {'showNsfw': True},
    )
    captured = {}

    def fake_paginate(*args, **kwargs):
        captured['unique'] = kwargs.get('unique')
        captured['transformer'] = kwargs.get('transformer')
        return type('Page', (), {'items': [], 'total': 0})()

    @contextmanager
    def fake_session_factory():
        yield object()

    monkeypatch.setattr(
        'domains.subscription.application.services.core.listing.service.paginate',
        fake_paginate,
    )
    svc.session_factory = fake_session_factory

    subscriptions, total = svc.list_subscriptions(
        user_id=1,
        query=None,
        type=None,
        nsfw='all',
        page=1,
        page_size=20,
    )

    assert subscriptions == []
    assert total == 0
    assert captured['unique'] is False


def test_list_subscriptions_filters_sync_issues_server_side():
    svc = SubscriptionListService(
        session_factory=_make_service().session_factory,
        get_user_config=lambda _user_id: {'showNsfw': True},
    )
    with svc.session_factory() as session:
        session.add_all(
            [
                Subscription(id=21, type='CHANNEL', name='Healthy', url='https://example.com/healthy'),
                Subscription(id=22, type='CHANNEL', name='Failed', url='https://example.com/failed'),
                Subscription(id=23, type='CHANNEL', name='Error detail', url='https://example.com/error'),
                UserSubscription(user_id=7, subscription_id=21, is_deleted=False),
                UserSubscription(user_id=7, subscription_id=22, is_deleted=False),
                UserSubscription(user_id=7, subscription_id=23, is_deleted=False),
                SubscriptionSyncState(
                    subscription_id=21,
                    sync_mode='incremental',
                    sync_status='success',
                ),
                SubscriptionSyncState(
                    subscription_id=22,
                    sync_mode='incremental',
                    sync_status='failed',
                ),
                SubscriptionSyncState(
                    subscription_id=23,
                    sync_mode='incremental',
                    sync_status='success',
                    last_error='extractor failed',
                ),
            ],
        )
        session.commit()

    subscriptions, total = svc.list_subscriptions(
        user_id=7,
        query=None,
        type=None,
        nsfw='all',
        page=1,
        page_size=20,
        status='issues',
    )

    assert total == 2
    assert {item['name'] for item in subscriptions} == {'Failed', 'Error detail'}
