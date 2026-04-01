from importlib import import_module
from pathlib import Path
import sys
from types import SimpleNamespace
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models import Base
from models.crawl_job import CrawlJob
from models.crawl_task import CrawlTask
from models.links import UserSubscription
from models.subscription import Subscription
from services.crawl_tasks import service as crawl_task_service
from services.subscription_update.models import UpdateMode, UpdateTrigger
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
    Base.metadata.create_all(engine, tables=[CrawlJob.__table__, CrawlTask.__table__])
    monkeypatch.setattr(crawl_task_service, 'get_session', lambda: _ManagedSession(engine))
    return engine


def _setup_subscription_store(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine, tables=[Subscription.__table__, UserSubscription.__table__])
    monkeypatch.setattr(scheduler_module, 'get_session', lambda: _ManagedSession(engine))
    return engine


def test_schedule_one_creates_subscription_sync_task_when_v2_enabled(monkeypatch):
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
    assert result.sync_state_id == 11
    assert result.run_id == 'run-1'

    with Session(engine, expire_on_commit=False) as session:
        jobs = session.query(CrawlJob).all()
        tasks = session.query(CrawlTask).all()

    assert len(jobs) == 1
    assert jobs[0].job_type == 'subscription_sync'
    assert jobs[0].source_type == 'manual'
    assert jobs[0].site == 'bilibili.com'
    assert len(tasks) == 1
    assert tasks[0].task_type == 'subscription_sync'
    assert tasks[0].subscription_id == 7
    assert tasks[0].payload['url'] == 'https://space.bilibili.com/42'
    assert tasks[0].payload['mode'] == 'full'
    assert tasks[0].payload['queue_token'] == 'queue-token-1'
    assert tasks[0].payload['run_id'] == 'run-1'
    assert tasks[0].payload['trace_id'] == 'trace-1'
    assert result.request_id == str(tasks[0].id)
    assert appended_events[-1].request_id == str(tasks[0].id)


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
