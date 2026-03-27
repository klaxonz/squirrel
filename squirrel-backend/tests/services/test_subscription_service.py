from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crawl import PluginInvokeResponse
from models import Base
from models.links import UserSubscription
from models.subscription import Subscription
from models.subscription_sync_state import SubscriptionSyncState
from services import subscription_service
from services import subscription_sync_state_service


@contextmanager
def _managed_session(engine):
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _setup_test_env(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            Subscription.__table__,
            UserSubscription.__table__,
            SubscriptionSyncState.__table__,
        ],
    )

    monkeypatch.setattr(subscription_service, 'get_session', lambda: _managed_session(engine))
    monkeypatch.setattr(subscription_sync_state_service, 'get_session', lambda: _managed_session(engine))
    return engine


def _seed_subscription(engine, *, subscription_id: int = 1, user_ids: list[int] | None = None):
    user_ids = user_ids or [1]
    with Session(engine, expire_on_commit=False) as session:
        subscription = Subscription(
            id=subscription_id,
            type='CHANNEL',
            name='Test subscription',
            url=f'https://www.youtube.com/channel/{subscription_id}',
            avatar=None,
            description=None,
            total_videos=0,
            is_deleted=False,
            extra_data={},
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )
        session.add(subscription)

        for index, user_id in enumerate(user_ids, start=1):
            session.add(
                UserSubscription(
                    id=index,
                    user_id=user_id,
                    subscription_id=subscription_id,
                    is_deleted=False,
                    is_nsfw=False,
                    created_at=datetime(2024, 1, 1),
                    updated_at=datetime(2024, 1, 1),
                )
            )

        session.add(
            SubscriptionSyncState(
                subscription_id=subscription_id,
                site='youtube',
                sync_mode='incremental',
                sync_status='queued',
                cursor_payload={},
                next_sync_at=datetime(2024, 1, 1, 1, 0, 0),
                queued_at=datetime(2024, 1, 1, 1, 0, 0),
                locked_at=datetime(2024, 1, 1, 1, 0, 0),
                pending_video_count=3,
                failure_count=0,
                idle_sync_count=0,
                version=0,
            )
        )
        session.commit()


def test_unsubscribe_by_id_deactivates_subscription_when_last_user_leaves(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_subscription(engine, user_ids=[1])

    result = subscription_service.unsubscribe_by_id(user_id=1, subscription_id=1)

    assert result is True

    with Session(engine, expire_on_commit=False) as session:
        subscription = session.get(Subscription, 1)
        user_subscription = session.query(UserSubscription).filter_by(user_id=1, subscription_id=1).one()
        sync_state = session.query(SubscriptionSyncState).filter_by(subscription_id=1).one()

    assert user_subscription.is_deleted is True
    assert subscription.is_deleted is True
    assert sync_state.sync_status == 'idle'
    assert sync_state.queue_token is None
    assert sync_state.queued_at is None
    assert sync_state.locked_at is None
    assert sync_state.pending_video_count == 0
    assert sync_state.last_error == 'no_active_subscribers'


def test_unsubscribe_by_id_keeps_subscription_active_when_other_users_remain(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_subscription(engine, user_ids=[1, 2])

    result = subscription_service.unsubscribe_by_id(user_id=1, subscription_id=1)

    assert result is True

    with Session(engine, expire_on_commit=False) as session:
        subscription = session.get(Subscription, 1)
        removed_link = session.query(UserSubscription).filter_by(user_id=1, subscription_id=1).one()
        remaining_link = session.query(UserSubscription).filter_by(user_id=2, subscription_id=1).one()
        sync_state = session.query(SubscriptionSyncState).filter_by(subscription_id=1).one()

    assert removed_link.is_deleted is True
    assert remaining_link.is_deleted is False
    assert subscription.is_deleted is False
    assert sync_state.sync_status == 'queued'
    assert sync_state.pending_video_count == 3


def test_preview_user_subscriptions_reads_items_from_plugin_gateway(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_subscription(engine, user_ids=[1])

    with Session(engine, expire_on_commit=False) as session:
        subscription = session.get(Subscription, 1)
        subscription.url = 'https://space.bilibili.com/1'
        session.commit()

    calls = []

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            calls.append({
                'capability': capability,
                'payload': payload,
                'site_name': site_name,
                'domain': domain,
                'timeout_ms': timeout_ms,
            })
            return PluginInvokeResponse(
                request_id='preview-1',
                ok=True,
                data={
                    'items': [
                        {'url': 'https://space.bilibili.com/1', 'name': 'Imported creator', 'avatar': 'https://img/1'},
                        {'url': 'https://space.bilibili.com/2', 'name': 'New creator', 'avatar': 'https://img/2'},
                    ],
                    'total': 2,
                },
            )

    monkeypatch.setattr(
        subscription_service,
        'get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )

    result = subscription_service.preview_user_subscriptions(site_name='bilibili', user_id=1)

    assert calls == [{
        'capability': 'import_subscriptions',
        'payload': None,
        'site_name': 'bilibili',
        'domain': None,
        'timeout_ms': None,
    }]
    assert result['site'] == 'bilibili'
    assert result['total'] == 2
    assert result['imported'] == 1
    assert result['not_imported'] == 1
    assert result['subscriptions'][0]['is_imported'] is True
    assert result['subscriptions'][0]['subscription_id'] == 1
    assert result['subscriptions'][1]['is_imported'] is False


def test_import_user_subscriptions_filters_gateway_items_before_enqueue(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_subscription(engine, user_ids=[1])

    with Session(engine, expire_on_commit=False) as session:
        subscription = session.get(Subscription, 1)
        subscription.url = 'https://space.bilibili.com/1'
        session.commit()

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            return PluginInvokeResponse(
                request_id='import-1',
                ok=True,
                data={
                    'items': [
                        {'url': 'https://space.bilibili.com/1', 'name': 'Existing creator'},
                        {'url': 'https://space.bilibili.com/2', 'name': 'Selected creator'},
                        {'url': 'https://space.bilibili.com/3', 'name': 'Ignored creator'},
                    ],
                    'total': 3,
                },
            )

    enqueued_batches = []

    class _ImmediateThread:
        def __init__(self, target=None, args=(), daemon=None):
            self._target = target
            self._args = args
            self.daemon = daemon

        def start(self):
            if self._target is not None:
                self._target(*self._args)

    monkeypatch.setattr(
        subscription_service,
        'get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )
    monkeypatch.setattr(
        subscription_service,
        '_enqueue_subscriptions_async',
        lambda subscriptions, user_id, site_name: enqueued_batches.append((subscriptions, user_id, site_name)),
    )
    monkeypatch.setattr(threading, 'Thread', _ImmediateThread)

    result = subscription_service.import_user_subscriptions(
        site_name='bilibili',
        user_id=1,
        selected_urls=[
            'https://space.bilibili.com/1',
            'https://space.bilibili.com/2',
        ],
    )

    assert result == {
        'total': 1,
        'found': 3,
        'selected': 2,
        'skipped': 1,
    }
    assert len(enqueued_batches) == 1
    queued_subscriptions, queued_user_id, queued_site_name = enqueued_batches[0]
    assert queued_user_id == 1
    assert queued_site_name == 'bilibili'
    assert [item.url for item in queued_subscriptions] == ['https://space.bilibili.com/2']
