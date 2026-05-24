from importlib import import_module
from pathlib import Path
import sys
from types import SimpleNamespace
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models import Base
from models.crawl_dispatch_scope import CrawlDispatchScope
from models.crawl_job import CrawlJob
from models.crawl_task import CrawlTask
from models.links import UserSubscription
from models.outbox_event import OutboxEvent
from models.subscription import Subscription
from models.subscription_sync_state import SubscriptionSyncState
from services.crawl_tasks import service as crawl_task_service
from services.subscription_update.models import SubscriptionUpdateResult, UpdateMode, UpdateTrigger
from services.subscription_update.scheduler import SubscriptionScheduler

scheduler_module = import_module('services.subscription_update.scheduler')


class _ManagedSession:
    def __init__(self, engine):
        self._session = Session(engine, expire_on_commit=False)

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self._session.rollback()
        else:
            self._session.commit()
        self._session.close()
        return False


def _setup_task_store(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[CrawlJob.__table__, CrawlTask.__table__, CrawlDispatchScope.__table__, OutboxEvent.__table__],
    )
    monkeypatch.setattr(crawl_task_service, 'get_session', lambda: _ManagedSession(engine))
    monkeypatch.setattr(scheduler_module.outbox_event_service, 'get_session', lambda: _ManagedSession(engine))
    return engine


def _setup_subscription_store(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[Subscription.__table__, UserSubscription.__table__, SubscriptionSyncState.__table__, OutboxEvent.__table__],
    )
    monkeypatch.setattr(scheduler_module, 'get_session', lambda: _ManagedSession(engine))
    monkeypatch.setattr(scheduler_module.subscription_sync_state_service, 'get_session', lambda: _ManagedSession(engine))
    monkeypatch.setattr(scheduler_module.outbox_event_service, 'get_session', lambda: _ManagedSession(engine))
    return engine


def test_schedule_one_publishes_full_sync_outbox_event_when_v2_enabled(monkeypatch):
    engine = _setup_task_store(monkeypatch)
    appended_events = []

    monkeypatch.setattr(scheduler_module.SiteCatalog, 'is_site_enabled', lambda domain=None, site=None: True)
    monkeypatch.setattr(SubscriptionScheduler, '_has_active_subscribers', staticmethod(lambda subscription_id: True))
    monkeypatch.setattr(
        scheduler_module.subscription_sync_state_service,
        'prepare_sync_state_for_enqueue',
        lambda subscription_id, url, mode, scheduled: (
            SimpleNamespace(id=11, pending_video_count=0, sync_mode=mode),
            'ready',
        ),
    )
    monkeypatch.setattr(
        scheduler_module.subscription_sync_state_service,
        'build_queue_token',
        lambda: 'queue-token-1',
    )
    monkeypatch.setattr(
        scheduler_module.subscription_sync_state_service,
        'queue_sync_state',
        lambda sync_state_id, queue_token: SimpleNamespace(
            id=11,
            queue_token=queue_token,
            sync_status='queued',
            queued_at='2026-04-01 12:00:00',
            pending_video_count=0,
        ),
    )
    monkeypatch.setattr(
        scheduler_module,
        'append_event',
        lambda event: appended_events.append(event),
    )

    result = SubscriptionScheduler().schedule_one(
        subscription_id=7,
        url='https://space.bilibili.com/42',
        trigger=UpdateTrigger.MANUAL,
        mode=UpdateMode.FULL,
        user_id=9,
        force=True,
        trace_id='trace-1',
        run_id='run-1',
    )

    assert result.status == 'queued'
    assert result.run_id == 'run-1'

    with Session(engine, expire_on_commit=False) as session:
        jobs = session.query(CrawlJob).all()
        tasks = session.query(CrawlTask).all()
        events = session.query(OutboxEvent).all()

    assert jobs == []
    assert tasks == []
    assert len(events) == 1
    assert events[0].event_type == 'full_sync_due'
    assert events[0].payload == {
        'subscription_id': 7,
        'mode': 'full',
        'trigger': 'manual',
        'url': 'https://space.bilibili.com/42',
        'site': 'bilibili.com',
        'user_id': 9,
        'force': True,
        'trace_id': 'trace-1',
        'run_id': 'run-1',
    }
    assert result.request_id == str(events[0].id)
    assert appended_events == []


def test_schedule_one_publishes_incremental_sync_outbox_event_for_incremental_mode(monkeypatch):
    engine = _setup_task_store(monkeypatch)
    appended_events = []

    monkeypatch.setattr(scheduler_module.SiteCatalog, 'is_site_enabled', lambda domain=None, site=None: True)
    monkeypatch.setattr(SubscriptionScheduler, '_has_active_subscribers', staticmethod(lambda subscription_id: True))
    monkeypatch.setattr(
        scheduler_module.subscription_sync_state_service,
        'prepare_sync_state_for_enqueue',
        lambda subscription_id, url, mode, scheduled: (
            SimpleNamespace(id=12, pending_video_count=0, sync_mode=mode),
            'ready',
        ),
    )
    monkeypatch.setattr(scheduler_module.subscription_sync_state_service, 'build_queue_token', lambda: 'queue-token-2')
    monkeypatch.setattr(
        scheduler_module.subscription_sync_state_service,
        'queue_sync_state',
        lambda sync_state_id, queue_token: SimpleNamespace(
            id=12,
            queue_token=queue_token,
            sync_status='queued',
            queued_at='2026-04-01 12:00:00',
            pending_video_count=0,
        ),
    )
    monkeypatch.setattr(scheduler_module, 'append_event', lambda event: appended_events.append(event))

    result = SubscriptionScheduler().schedule_one(
        subscription_id=8,
        url='https://space.bilibili.com/43',
        trigger=UpdateTrigger.SCHEDULED,
        mode=UpdateMode.INCREMENTAL,
        trace_id='trace-2',
        run_id='run-2',
    )

    assert result.status == 'queued'

    with Session(engine, expire_on_commit=False) as session:
        jobs = session.query(CrawlJob).all()
        tasks = session.query(CrawlTask).all()
        events = session.query(OutboxEvent).all()

    assert jobs == []
    assert tasks == []
    assert len(events) == 1
    assert events[0].event_type == 'incremental_sync_due'
    assert events[0].payload['subscription_id'] == 8
    assert events[0].payload['mode'] == 'incremental'
    assert events[0].payload['trigger'] == 'scheduled'
    assert events[0].payload['run_id'] == 'run-2'
    assert result.request_id == str(events[0].id)
    assert appended_events == []


def test_run_one_inline_executes_sync_and_video_extraction_without_crawl_task(monkeypatch):
    appended_events = []
    payloads = []

    monkeypatch.setattr(scheduler_module.SiteCatalog, 'is_site_enabled', lambda domain=None, site=None: True)
    monkeypatch.setattr(SubscriptionScheduler, '_has_active_subscribers', staticmethod(lambda subscription_id: True))
    monkeypatch.setattr(
        scheduler_module.subscription_sync_state_service,
        'prepare_sync_state_for_enqueue',
        lambda subscription_id, url, mode, scheduled: (
            SimpleNamespace(id=21, pending_video_count=0, sync_mode=mode),
            'ready',
        ),
    )
    monkeypatch.setattr(scheduler_module.subscription_sync_state_service, 'build_queue_token', lambda: 'queue-token-3')
    monkeypatch.setattr(
        scheduler_module.subscription_sync_state_service,
        'queue_sync_state',
        lambda sync_state_id, queue_token: SimpleNamespace(
            id=21,
            queue_token=queue_token,
            sync_status='queued',
            queued_at='2026-04-01 12:00:00',
            pending_video_count=0,
        ),
    )
    monkeypatch.setattr(scheduler_module, 'append_event', lambda event: appended_events.append(event))
    monkeypatch.setattr(
        'services.crawl_executors.subscription_sync_executor.execute_subscription_sync_payload',
        lambda payload: payloads.append(payload) or SubscriptionUpdateResult(
            subscription_id=payload['subscription_id'],
            success=True,
            videos_found=2,
            videos_enqueued=2,
        ),
    )

    result = SubscriptionScheduler().run_one_inline(
        subscription_id=9,
        url='https://space.bilibili.com/44',
        trigger=UpdateTrigger.MANUAL,
        mode=UpdateMode.INCREMENTAL,
        user_id=7,
        trace_id='trace-3',
        run_id='run-3',
    )

    assert result.status == 'success'
    assert result.request_id == 'direct:run-3'
    assert result.sync_state_id == 21
    assert result.result.videos_enqueued == 2
    assert payloads == [{
        'subscription_id': 9,
        'url': 'https://space.bilibili.com/44',
        'sync_state_id': 21,
        'mode': 'incremental',
        'user_id': 7,
        'force': False,
        'queue_token': 'queue-token-3',
        'trigger': 'manual',
        'run_id': 'run-3',
        'trace_id': 'trace-3',
        'request_id': 'direct:run-3',
        'inline_video_extraction': True,
    }]
    assert [event.event_type for event in appended_events] == ['queued']


def test_enqueue_all_active_includes_active_subscriptions_without_sync_state(monkeypatch):
    engine = _setup_subscription_store(monkeypatch)

    with Session(engine, expire_on_commit=False) as session:
        session.add_all(
            [
                Subscription(id=1, type='CHANNEL', name='due-no-state', url='https://space.bilibili.com/1', is_deleted=False),
                Subscription(id=2, type='CHANNEL', name='due-existing-state', url='https://space.bilibili.com/2', is_deleted=False),
                Subscription(id=3, type='CHANNEL', name='not-due', url='https://space.bilibili.com/3', is_deleted=False),
                Subscription(id=4, type='CHANNEL', name='no-subscriber', url='https://space.bilibili.com/4', is_deleted=False),
                Subscription(id=5, type='CHANNEL', name='deleted', url='https://space.bilibili.com/5', is_deleted=True),
            ]
        )
        session.add_all(
            [
                UserSubscription(user_id=100, subscription_id=1, is_deleted=False, is_nsfw=False),
                UserSubscription(user_id=100, subscription_id=2, is_deleted=False, is_nsfw=False),
                UserSubscription(user_id=100, subscription_id=3, is_deleted=False, is_nsfw=False),
            ]
        )
        session.commit()

    now = datetime.now()
    sync_states = {
        2: SimpleNamespace(sync_status='success', next_sync_at=now - timedelta(minutes=1)),
        3: SimpleNamespace(sync_status='success', next_sync_at=now + timedelta(minutes=10)),
    }
    scheduled_calls = []

    monkeypatch.setattr(
        scheduler_module.subscription_sync_state_service,
        'get_sync_state',
        lambda subscription_id, mode: sync_states.get(subscription_id),
    )
    monkeypatch.setattr(
        SubscriptionScheduler,
        'schedule_one',
        lambda self, subscription_id, url, trigger, mode: (
            scheduled_calls.append((subscription_id, url, trigger, mode)) or
            SimpleNamespace(status='queued')
        ),
    )

    success, failed = SubscriptionScheduler().enqueue_all_active(
        trigger=UpdateTrigger.SCHEDULED,
        mode=UpdateMode.INCREMENTAL,
    )

    assert failed == 0
    assert success == 2
    assert scheduled_calls == [
        (1, 'https://space.bilibili.com/1', UpdateTrigger.SCHEDULED, UpdateMode.INCREMENTAL),
        (2, 'https://space.bilibili.com/2', UpdateTrigger.SCHEDULED, UpdateMode.INCREMENTAL),
    ]


def test_enqueue_all_active_counts_failed_results(monkeypatch):
    engine = _setup_subscription_store(monkeypatch)

    with Session(engine, expire_on_commit=False) as session:
        session.add_all(
            [
                Subscription(id=1, type='CHANNEL', name='ok', url='https://space.bilibili.com/1', is_deleted=False),
                Subscription(id=2, type='CHANNEL', name='bad', url='https://space.bilibili.com/2', is_deleted=False),
            ]
        )
        session.add_all(
            [
                UserSubscription(user_id=100, subscription_id=1, is_deleted=False, is_nsfw=False),
                UserSubscription(user_id=100, subscription_id=2, is_deleted=False, is_nsfw=False),
            ]
        )
        session.commit()

    monkeypatch.setattr(
        scheduler_module.subscription_sync_state_service,
        'get_sync_state',
        lambda subscription_id, mode: None,
    )
    monkeypatch.setattr(
        SubscriptionScheduler,
        'schedule_one',
        lambda self, subscription_id, url, trigger, mode: SimpleNamespace(
            status='queued' if subscription_id == 1 else 'failed',
        ),
    )

    success, failed = SubscriptionScheduler().enqueue_all_active(
        trigger=UpdateTrigger.SCHEDULED,
        mode=UpdateMode.INCREMENTAL,
    )

    assert (success, failed) == (1, 1)


def test_enqueue_due_states_publishes_outbox_events_from_sync_state_store(monkeypatch):
    engine = _setup_subscription_store(monkeypatch)
    now = datetime(2026, 4, 4, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        session.add_all(
            [
                Subscription(id=1, type='CHANNEL', name='due-1', url='https://space.bilibili.com/1', is_deleted=False),
                Subscription(id=2, type='CHANNEL', name='due-2', url='https://space.bilibili.com/2', is_deleted=False),
            ]
        )
        session.add_all(
            [
                UserSubscription(user_id=100, subscription_id=1, is_deleted=False, is_nsfw=False),
                UserSubscription(user_id=100, subscription_id=2, is_deleted=False, is_nsfw=False),
            ]
        )
        session.add_all(
            [
                SubscriptionSyncState(
                    id=11,
                    subscription_id=1,
                    site='bilibili.com',
                    sync_mode='incremental',
                    sync_status='success',
                    next_sync_at=now - timedelta(minutes=1),
                ),
                SubscriptionSyncState(
                    id=12,
                    subscription_id=2,
                    site='bilibili.com',
                    sync_mode='incremental',
                    sync_status='success',
                    next_sync_at=now - timedelta(minutes=2),
                ),
            ]
        )
        session.commit()

    success, failed = SubscriptionScheduler().enqueue_due_states(
        trigger=UpdateTrigger.SCHEDULED,
        mode=UpdateMode.INCREMENTAL,
        now=now,
    )

    assert (success, failed) == (2, 0)

    with Session(engine, expire_on_commit=False) as session:
        events = session.query(OutboxEvent).order_by(OutboxEvent.id.asc()).all()

    assert [event.event_type for event in events] == ['incremental_sync_due', 'incremental_sync_due']
    assert [event.payload['sync_state_id'] for event in events] == [12, 11]
