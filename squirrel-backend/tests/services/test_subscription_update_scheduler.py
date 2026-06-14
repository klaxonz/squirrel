from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from domains.subscription.application.services.core.update.commands import SubscriptionSyncCommandService
from domains.subscription.application.services.core.update.models import (
    SubscriptionUpdateResult,
    UpdateMode,
    UpdateTrigger,
)
from domains.subscription.application.services.core.update.scheduler import SubscriptionScheduler
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.crawl_dispatch_scope import CrawlDispatchScope
from domains.subscription.domain.models.crawl_job import CrawlJob
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.subscription.domain.models.subscription import Subscription
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState
from shared_kernel.domain.base import Base


@pytest.fixture
def engine(engine):
    Base.metadata.create_all(
        engine,
        tables=[
            CrawlJob.__table__,
            CrawlTask.__table__,
            CrawlDispatchScope.__table__,
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
    from infrastructure.database import session as database

    with patch.object(database, 'register_after_commit', lambda session, callback: None), \
         patch.object(database, 'get_session', session_factory):
        yield


def test_schedule_one_creates_full_sync_crawl_task(engine, session_factory, sched):
    appended_events = []

    import subscription.services.core.sync.state.service as ssss

    from domains.subscription.application.services.crawl.tasks import service as crawl_task_service_mod
    from domains.subscription.application.services.crawl.tasks.service import CrawlTaskService

    injected_cts = CrawlTaskService(session_factory=session_factory)

    with patch('services.site_catalog.catalog.SiteCatalog.is_site_enabled', return_value=True), \
         patch.object(SubscriptionSyncCommandService, '_has_active_subscribers', return_value=True), \
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
         patch('services.subscription.update.command_events.append_event', lambda event: appended_events.append(event)), \
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

    assert len(jobs) == 1
    assert jobs[0].job_type == "subscription_sync"
    assert jobs[0].site == "bilibili.com"
    assert len(tasks) == 1
    assert tasks[0].task_type == "subscription_sync_full"
    assert tasks[0].payload["subscription_id"] == 7
    assert tasks[0].payload["mode"] == "full"
    assert tasks[0].payload["trigger"] == "manual"
    assert tasks[0].payload["run_id"] == "run-1"
    assert tasks[0].payload["request_id"] == str(tasks[0].id)
    assert result.request_id == str(tasks[0].id)
    assert [event.event_type for event in appended_events] == ["queued"]


def test_schedule_one_creates_incremental_sync_crawl_task(engine, session_factory, sched):
    appended_events = []

    import subscription.services.core.sync.state.service as ssss

    from domains.subscription.application.services.crawl.tasks import service as crawl_task_service_mod
    from domains.subscription.application.services.crawl.tasks.service import CrawlTaskService

    injected_cts = CrawlTaskService(session_factory=session_factory)

    with patch('services.site_catalog.catalog.SiteCatalog.is_site_enabled', return_value=True), \
         patch.object(SubscriptionSyncCommandService, '_has_active_subscribers', return_value=True), \
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
         patch('services.subscription.update.command_events.append_event', lambda event: appended_events.append(event)), \
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

    assert len(jobs) == 1
    assert len(tasks) == 1
    assert tasks[0].task_type == "subscription_sync_incremental"
    assert tasks[0].payload["subscription_id"] == 8
    assert tasks[0].payload["mode"] == "incremental"
    assert tasks[0].payload["trigger"] == "scheduled"
    assert tasks[0].payload["run_id"] == "run-2"
    assert result.request_id == str(tasks[0].id)
    assert [event.event_type for event in appended_events] == ["queued"]


def test_run_one_inline_executes_sync_and_video_extraction_without_crawl_task(engine, session_factory, sched):
    appended_events = []
    payloads = []

    import subscription.services.core.sync.state.service as ssss

    with patch('services.site_catalog.catalog.SiteCatalog.is_site_enabled', return_value=True), \
         patch.object(SubscriptionSyncCommandService, '_has_active_subscribers', return_value=True), \
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
         patch('services.subscription.update.command_events.append_event', lambda event: appended_events.append(event)), \
         patch(
             'services.crawl.executors.subscription_sync_executor.execute_subscription_sync_payload',
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

    import subscription.services.core.sync.state.service as ssss

    with patch.object(ssss, 'get_sync_state', lambda subscription_id, mode: None), \
         patch.object(SubscriptionScheduler, 'schedule_one', lambda self, subscription_id, url, trigger, mode: SimpleNamespace(
             status="queued" if subscription_id == 1 else "failed",
         )):

        success, failed = sched.enqueue_all_active(
            trigger=UpdateTrigger.SCHEDULED,
            mode=UpdateMode.INCREMENTAL,
        )

    assert (success, failed) == (1, 1)


def test_enqueue_due_states_creates_crawl_tasks_from_sync_state_store(engine, session_factory, sched):
    now = datetime(2026, 4, 4, 12, 0, 0)
    appended_events = []

    from domains.subscription.application.services.crawl.tasks import service as crawl_task_service_mod
    from domains.subscription.application.services.crawl.tasks.service import CrawlTaskService

    injected_cts = CrawlTaskService(session_factory=session_factory)

    with patch('services.subscription.update.command_events.append_event', lambda event: appended_events.append(event)), \
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
        tasks = session.query(CrawlTask).order_by(CrawlTask.id.asc()).all()

    assert [task.task_type for task in tasks] == ["subscription_sync_incremental", "subscription_sync_incremental"]
    assert [task.payload["sync_state_id"] for task in tasks] == [12, 11]
    assert [event.event_type for event in appended_events] == ["run_created", "queued", "run_created", "queued"]
