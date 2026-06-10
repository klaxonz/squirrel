from datetime import datetime, timedelta
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from models import Base
from models.crawl_dispatch_scope import CrawlDispatchScope
from models.crawl_job import CrawlJob
from models.crawl_task import CrawlTask
from models.links import UserSubscription
from models.outbox_event import OutboxEvent
from models.subscription import Subscription
from models.subscription_sync_state import SubscriptionSyncState
from services.outbox_event_service import OutboxEventService
from services.subscription_update.models import SubscriptionUpdateResult, UpdateMode, UpdateTrigger
from services.subscription_update.scheduler import SubscriptionScheduler


@pytest.fixture
def engine(engine):
    Base.metadata.create_all(
        engine,
        tables=[
            CrawlJob.__table__,
            CrawlTask.__table__,
            CrawlDispatchScope.__table__,
            OutboxEvent.__table__,
            Subscription.__table__,
            UserSubscription.__table__,
            SubscriptionSyncState.__table__,
        ],
    )
    return engine


@pytest.fixture
def sched(session_factory):
    return SubscriptionScheduler(session_factory=session_factory)


@pytest.fixture(autouse=True)
def _patch_postgres(session_factory):
    """Patch postgres-specific calls to work with SQLite."""
    from core import database
    from services.subscription_sync_projection_service import _default as proj_default
    from services.subscription_sync_run_service import _default as run_svc_default

    scheduler_mod = import_module('services.subscription_update.scheduler')

    with patch.object(database, 'register_after_commit', lambda session, callback: None), \
         patch.object(database, 'get_session', session_factory), \
         patch.object(scheduler_mod, 'outbox_event_service', OutboxEventService(session_factory=session_factory)), \
         patch.object(run_svc_default, 'next_seq_no', lambda stream_id, *, session=None: 1), \
         patch.object(proj_default, '_advisory_lock', staticmethod(lambda session, key: None)), \
         patch.object(proj_default, 'apply_event', lambda event, session=None: event):
        yield


def test_schedule_one_publishes_full_sync_outbox_event_when_v2_enabled(engine, session_factory, sched):
    appended_events = []

    from services import subscription_sync_state_service as ssss
    from services.crawl_tasks import service as crawl_task_service_mod
    from services.crawl_tasks.service import CrawlTaskService

    injected_cts = CrawlTaskService(session_factory=session_factory)

    with patch.object(ssss, '_resolve_site', return_value='bilibili.com', create=True), \
         patch('utils.site_catalog.SiteCatalog.is_site_enabled', return_value=True), \
         patch.object(SubscriptionScheduler, '_has_active_subscribers', return_value=True), \
         patch.object(ssss, 'prepare_sync_state_for_enqueue', return_value=(
             SimpleNamespace(id=11, pending_video_count=0, sync_mode=UpdateMode.FULL),
             "ready",
         )), \
         patch.object(ssss, 'build_queue_token', return_value="queue-token-1"), \
         patch.object(ssss, 'queue_sync_state', return_value=SimpleNamespace(
             id=11,
             queue_token="queue-token-1",
             sync_status="queued",
             queued_at="2026-04-01 12:00:00",
             pending_video_count=0,
         )), \
         patch('services.subscription_update.scheduler.append_event', lambda event: appended_events.append(event)), \
         patch.object(crawl_task_service_mod, 'create_job_with_task', injected_cts.create_job_with_task), \
         patch.object(crawl_task_service_mod, 'create_job', injected_cts.create_job), \
         patch.object(crawl_task_service_mod, 'create_task', injected_cts.create_task), \
         patch.object(crawl_task_service_mod, 'recover_expired_tasks', injected_cts.recover_expired_tasks), \
         patch.object(crawl_task_service_mod, 'claim_next_task', injected_cts.claim_next_task), \
         patch.object(crawl_task_service_mod, 'start_task', injected_cts.start_task), \
         patch.object(crawl_task_service_mod, 'complete_task', injected_cts.complete_task), \
         patch.object(crawl_task_service_mod, 'cancel_task', injected_cts.cancel_task), \
         patch.object(crawl_task_service_mod, 'replay_dead_task', injected_cts.replay_dead_task), \
         patch.object(crawl_task_service_mod, 'retry_task', injected_cts.retry_task), \
         patch.object(crawl_task_service_mod, 'renew_task_lease', injected_cts.renew_task_lease), \
         patch.object(crawl_task_service_mod, 'clear_task_dedupe_key', injected_cts.clear_task_dedupe_key):

        result = sched.schedule_one(
            subscription_id=7,
            url="https://space.bilibili.com/42",
            trigger=UpdateTrigger.MANUAL,
            mode=UpdateMode.FULL,
            user_id=9,
            force=True,
            trace_id="trace-1",
            run_id="run-1",
        )

    assert result.status == "queued"
    assert result.run_id == "run-1"

    with Session(engine, expire_on_commit=False) as session:
        jobs = session.query(CrawlJob).all()
        tasks = session.query(CrawlTask).all()
        events = session.query(OutboxEvent).all()

    assert jobs == []
    assert tasks == []
    assert len(events) == 1
    assert events[0].event_type == "full_sync_due"
    assert events[0].payload == {
        "subscription_id": 7,
        "mode": "full",
        "trigger": "manual",
        "url": "https://space.bilibili.com/42",
        "site": "bilibili.com",
        "user_id": 9,
        "force": True,
        "trace_id": "trace-1",
        "run_id": "run-1",
    }
    assert result.request_id == str(events[0].id)
    assert appended_events == []


def test_schedule_one_publishes_incremental_sync_outbox_event_for_incremental_mode(engine, session_factory, sched):
    appended_events = []

    from services import subscription_sync_state_service as ssss
    from services.crawl_tasks import service as crawl_task_service_mod
    from services.crawl_tasks.service import CrawlTaskService

    injected_cts = CrawlTaskService(session_factory=session_factory)

    with patch.object(ssss, '_resolve_site', return_value='bilibili.com', create=True), \
         patch('utils.site_catalog.SiteCatalog.is_site_enabled', return_value=True), \
         patch.object(SubscriptionScheduler, '_has_active_subscribers', return_value=True), \
         patch.object(ssss, 'prepare_sync_state_for_enqueue', return_value=(
             SimpleNamespace(id=12, pending_video_count=0, sync_mode=UpdateMode.INCREMENTAL),
             "ready",
         )), \
         patch.object(ssss, 'build_queue_token', return_value="queue-token-2"), \
         patch.object(ssss, 'queue_sync_state', return_value=SimpleNamespace(
             id=12,
             queue_token="queue-token-2",
             sync_status="queued",
             queued_at="2026-04-01 12:00:00",
             pending_video_count=0,
         )), \
         patch('services.subscription_update.scheduler.append_event', lambda event: appended_events.append(event)), \
         patch.object(crawl_task_service_mod, 'create_job_with_task', injected_cts.create_job_with_task), \
         patch.object(crawl_task_service_mod, 'create_job', injected_cts.create_job), \
         patch.object(crawl_task_service_mod, 'create_task', injected_cts.create_task), \
         patch.object(crawl_task_service_mod, 'recover_expired_tasks', injected_cts.recover_expired_tasks), \
         patch.object(crawl_task_service_mod, 'claim_next_task', injected_cts.claim_next_task), \
         patch.object(crawl_task_service_mod, 'start_task', injected_cts.start_task), \
         patch.object(crawl_task_service_mod, 'complete_task', injected_cts.complete_task), \
         patch.object(crawl_task_service_mod, 'cancel_task', injected_cts.cancel_task), \
         patch.object(crawl_task_service_mod, 'replay_dead_task', injected_cts.replay_dead_task), \
         patch.object(crawl_task_service_mod, 'retry_task', injected_cts.retry_task), \
         patch.object(crawl_task_service_mod, 'renew_task_lease', injected_cts.renew_task_lease), \
         patch.object(crawl_task_service_mod, 'clear_task_dedupe_key', injected_cts.clear_task_dedupe_key):

        result = sched.schedule_one(
            subscription_id=8,
            url="https://space.bilibili.com/43",
            trigger=UpdateTrigger.SCHEDULED,
            mode=UpdateMode.INCREMENTAL,
            trace_id="trace-2",
            run_id="run-2",
        )

    assert result.status == "queued"

    with Session(engine, expire_on_commit=False) as session:
        jobs = session.query(CrawlJob).all()
        tasks = session.query(CrawlTask).all()
        events = session.query(OutboxEvent).all()

    assert jobs == []
    assert tasks == []
    assert len(events) == 1
    assert events[0].event_type == "incremental_sync_due"
    assert events[0].payload["subscription_id"] == 8
    assert events[0].payload["mode"] == "incremental"
    assert events[0].payload["trigger"] == "scheduled"
    assert events[0].payload["run_id"] == "run-2"
    assert result.request_id == str(events[0].id)
    assert appended_events == []


def test_run_one_inline_executes_sync_and_video_extraction_without_crawl_task(engine, session_factory, sched):
    appended_events = []
    payloads = []

    from services import subscription_sync_state_service as ssss

    with patch.object(ssss, '_resolve_site', return_value='bilibili.com', create=True), \
         patch('utils.site_catalog.SiteCatalog.is_site_enabled', return_value=True), \
         patch.object(SubscriptionScheduler, '_has_active_subscribers', return_value=True), \
         patch.object(ssss, 'prepare_sync_state_for_enqueue', return_value=(
             SimpleNamespace(id=21, pending_video_count=0, sync_mode=UpdateMode.INCREMENTAL),
             "ready",
         )), \
         patch.object(ssss, 'build_queue_token', return_value="queue-token-3"), \
         patch.object(ssss, 'queue_sync_state', return_value=SimpleNamespace(
             id=21,
             queue_token="queue-token-3",
             sync_status="queued",
             queued_at="2026-04-01 12:00:00",
             pending_video_count=0,
         )), \
         patch('services.subscription_update.scheduler.append_event', lambda event: appended_events.append(event)), \
         patch(
             'services.crawl_executors.subscription_sync_executor.execute_subscription_sync_payload',
             lambda payload: payloads.append(payload) or SubscriptionUpdateResult(
                 subscription_id=payload["subscription_id"],
                 success=True,
                 videos_found=2,
                 videos_enqueued=2,
             ),
         ):

        result = sched.run_one_inline(
            subscription_id=9,
            url="https://space.bilibili.com/44",
            trigger=UpdateTrigger.MANUAL,
            mode=UpdateMode.INCREMENTAL,
            user_id=7,
            trace_id="trace-3",
            run_id="run-3",
        )

    assert result.status == "success"
    assert result.request_id == "direct:run-3"
    assert result.sync_state_id == 21
    assert result.result.videos_enqueued == 2
    assert payloads == [{
        "subscription_id": 9,
        "url": "https://space.bilibili.com/44",
        "sync_state_id": 21,
        "mode": "incremental",
        "user_id": 7,
        "force": False,
        "queue_token": "queue-token-3",
        "trigger": "manual",
        "run_id": "run-3",
        "trace_id": "trace-3",
        "request_id": "direct:run-3",
        "inline_video_extraction": True,
    }]
    assert [event.event_type for event in appended_events] == ["queued"]


def test_enqueue_all_active_includes_active_subscriptions_without_sync_state(engine, session_factory, sched):
    with Session(engine, expire_on_commit=False) as session:
        session.add_all(
            [
                Subscription(id=1, type="CHANNEL", name="due-no-state", url="https://space.bilibili.com/1", is_deleted=False),
                Subscription(id=2, type="CHANNEL", name="due-existing-state", url="https://space.bilibili.com/2", is_deleted=False),
                Subscription(id=3, type="CHANNEL", name="not-due", url="https://space.bilibili.com/3", is_deleted=False),
                Subscription(id=4, type="CHANNEL", name="no-subscriber", url="https://space.bilibili.com/4", is_deleted=False),
                Subscription(id=5, type="CHANNEL", name="deleted", url="https://space.bilibili.com/5", is_deleted=True),
            ],
        )
        session.add_all(
            [
                UserSubscription(user_id=100, subscription_id=1, is_deleted=False, is_nsfw=False),
                UserSubscription(user_id=100, subscription_id=2, is_deleted=False, is_nsfw=False),
                UserSubscription(user_id=100, subscription_id=3, is_deleted=False, is_nsfw=False),
            ],
        )
        now = datetime.now()
        session.add_all(
            [
                SubscriptionSyncState(
                    subscription_id=2,
                    site="bilibili.com",
                    sync_mode="incremental",
                    sync_status="success",
                    next_sync_at=now - timedelta(minutes=1),
                ),
                SubscriptionSyncState(
                    subscription_id=3,
                    site="bilibili.com",
                    sync_mode="incremental",
                    sync_status="success",
                    next_sync_at=now + timedelta(minutes=10),
                ),
            ],
        )
        session.commit()

    scheduled_calls = []

    with patch.object(SubscriptionScheduler, 'schedule_one', lambda self, subscription_id, url, trigger, mode: (
             scheduled_calls.append((subscription_id, url, trigger, mode)) or
             SimpleNamespace(status="queued")
         )):

        success, failed = sched.enqueue_all_active(
            trigger=UpdateTrigger.SCHEDULED,
            mode=UpdateMode.INCREMENTAL,
        )

    assert failed == 0
    assert success == 2
    assert scheduled_calls == [
        (1, "https://space.bilibili.com/1", UpdateTrigger.SCHEDULED, UpdateMode.INCREMENTAL),
        (2, "https://space.bilibili.com/2", UpdateTrigger.SCHEDULED, UpdateMode.INCREMENTAL),
    ]


def test_enqueue_all_active_counts_failed_results(engine, session_factory, sched):
    with Session(engine, expire_on_commit=False) as session:
        session.add_all(
            [
                Subscription(id=1, type="CHANNEL", name="ok", url="https://space.bilibili.com/1", is_deleted=False),
                Subscription(id=2, type="CHANNEL", name="bad", url="https://space.bilibili.com/2", is_deleted=False),
            ],
        )
        session.add_all(
            [
                UserSubscription(user_id=100, subscription_id=1, is_deleted=False, is_nsfw=False),
                UserSubscription(user_id=100, subscription_id=2, is_deleted=False, is_nsfw=False),
            ],
        )
        session.commit()

    from services import subscription_sync_state_service as ssss

    with patch.object(ssss, 'get_sync_state', lambda subscription_id, mode: None), \
         patch.object(SubscriptionScheduler, 'schedule_one', lambda self, subscription_id, url, trigger, mode: SimpleNamespace(
             status="queued" if subscription_id == 1 else "failed",
         )):

        success, failed = sched.enqueue_all_active(
            trigger=UpdateTrigger.SCHEDULED,
            mode=UpdateMode.INCREMENTAL,
        )

    assert (success, failed) == (1, 1)


def test_enqueue_due_states_publishes_outbox_events_from_sync_state_store(engine, session_factory, sched):
    now = datetime(2026, 4, 4, 12, 0, 0)

    from services.crawl_tasks import service as crawl_task_service_mod
    from services.crawl_tasks.service import CrawlTaskService

    injected_cts = CrawlTaskService(session_factory=session_factory)

    with patch.object(crawl_task_service_mod, 'create_job_with_task', injected_cts.create_job_with_task), \
         patch.object(crawl_task_service_mod, 'create_job', injected_cts.create_job), \
         patch.object(crawl_task_service_mod, 'create_task', injected_cts.create_task), \
         patch.object(crawl_task_service_mod, 'recover_expired_tasks', injected_cts.recover_expired_tasks), \
         patch.object(crawl_task_service_mod, 'claim_next_task', injected_cts.claim_next_task), \
         patch.object(crawl_task_service_mod, 'start_task', injected_cts.start_task), \
         patch.object(crawl_task_service_mod, 'complete_task', injected_cts.complete_task), \
         patch.object(crawl_task_service_mod, 'cancel_task', injected_cts.cancel_task), \
         patch.object(crawl_task_service_mod, 'replay_dead_task', injected_cts.replay_dead_task), \
         patch.object(crawl_task_service_mod, 'retry_task', injected_cts.retry_task), \
         patch.object(crawl_task_service_mod, 'renew_task_lease', injected_cts.renew_task_lease), \
         patch.object(crawl_task_service_mod, 'clear_task_dedupe_key', injected_cts.clear_task_dedupe_key):

        with Session(engine, expire_on_commit=False) as session:
            session.add_all(
                [
                    Subscription(id=1, type="CHANNEL", name="due-1", url="https://space.bilibili.com/1", is_deleted=False),
                    Subscription(id=2, type="CHANNEL", name="due-2", url="https://space.bilibili.com/2", is_deleted=False),
                ],
            )
            session.add_all(
                [
                    UserSubscription(user_id=100, subscription_id=1, is_deleted=False, is_nsfw=False),
                    UserSubscription(user_id=100, subscription_id=2, is_deleted=False, is_nsfw=False),
                ],
            )
            session.add_all(
                [
                    SubscriptionSyncState(
                        id=11,
                        subscription_id=1,
                        site="bilibili.com",
                        sync_mode="incremental",
                        sync_status="success",
                        next_sync_at=now - timedelta(minutes=1),
                    ),
                    SubscriptionSyncState(
                        id=12,
                        subscription_id=2,
                        site="bilibili.com",
                        sync_mode="incremental",
                        sync_status="success",
                        next_sync_at=now - timedelta(minutes=2),
                    ),
                ],
            )
            session.commit()

        success, failed = sched.enqueue_due_states(
            trigger=UpdateTrigger.SCHEDULED,
            mode=UpdateMode.INCREMENTAL,
            now=now,
        )

    assert (success, failed) == (2, 0)

    with Session(engine, expire_on_commit=False) as session:
        events = session.query(OutboxEvent).order_by(OutboxEvent.id.asc()).all()

    assert [event.event_type for event in events] == ["incremental_sync_due", "incremental_sync_due"]
    assert [event.payload["sync_state_id"] for event in events] == [12, 11]
