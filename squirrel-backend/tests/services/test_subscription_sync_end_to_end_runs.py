from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

import domains.subscription.application.services.core.sync.state.service as subscription_sync_state_service
from domains.subscription.application.services.core.crud import SubscriptionCrudService
from domains.subscription.application.services.core.sync.run_service import SubscriptionSyncRunService
from domains.subscription.application.services.crawl.tasks.errors import CrawlTaskStateError
from domains.subscription.application.services.crawl.tasks.service import CrawlTaskService
from domains.subscription.domain.models.crawl_job import CrawlJob
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.subscription.domain.models.subscription_sync_run import SubscriptionSyncRun
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState
from domains.video.application.services.extraction.task_service import VideoExtractionTaskService
from domains.video.interfaces.dto.video_dto import VideoExtractDto
from infrastructure.database.base import Base


@pytest.fixture
def engine(engine):
    return engine


@pytest.fixture
def sss_session_patch(session_factory):
    """Redirect module-level services to use test session_factory."""
    from infrastructure.database import session as database

    with patch.object(database, 'get_session', session_factory):
        yield


def _setup_state_env(engine):
    Base.metadata.create_all(
        engine,
        tables=[
            SubscriptionSyncState.__table__,
            SubscriptionSyncRun.__table__,
            CrawlJob.__table__,
            CrawlTask.__table__,
        ],
    )
    return engine


def test_mark_sync_success_stays_running_until_pending_videos_are_drained(engine, session_factory, sss_session_patch):
    engine = _setup_state_env(engine)
    sss_svc = subscription_sync_state_service

    now = datetime(2026, 4, 2, 12, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=11,
                subscription_id=1,
                site='youtube.com',
                sync_mode='incremental',
                sync_status='running',
                cursor_payload={'cursor': 'done'},
                last_seen_video_url='https://example.com/video/1',
                last_sync_at=now - timedelta(minutes=1),
                last_success_at=None,
                next_sync_at=now + timedelta(minutes=5),
                queued_at=now - timedelta(minutes=2),
                locked_at=now - timedelta(minutes=2),
                queue_token='queue-token',
                current_run_id='run-11',
                execution_token='direct:run-11',
                pending_video_count=3,
                failure_count=0,
                idle_sync_count=0,
                version=0,
                last_error=None,
                created_at=now - timedelta(hours=1),
                updated_at=now - timedelta(minutes=2),
            ),
        )
        session.add(
            SubscriptionSyncRun(
                id='run-11',
                subscription_id=1,
                sync_state_id=11,
                site='youtube',
                sync_mode='incremental',
                status='running',
            ),
        )
        job = CrawlJob(job_type='video_extract', source_type='scheduled', site='youtube')
        session.add(job)
        session.flush()
        session.add_all(
            [
                CrawlTask(
                    job_id=job.id,
                    task_type='video_extract',
                    site='youtube',
                    sync_state_id=11,
                    run_id='run-11',
                    status='pending',
                )
                for _ in range(3)
            ],
        )
        session.commit()

    sss_svc.mark_sync_success(
        11,
        cursor_payload={'cursor': 'done'},
        latest_video_url='https://example.com/video/1',
        videos_found=10,
        run_id='run-11',
        queue_token='queue-token',
        execution_token='direct:run-11',
    )

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 11)

    # pending videos remain -> stays running, success not finalized
    assert state.sync_status == 'running'
    assert state.locked_at is None
    assert state.pending_video_count == 3
    assert state.last_success_at is None

    with Session(engine, expire_on_commit=False) as session:
        for task in session.query(CrawlTask).filter(CrawlTask.run_id == 'run-11'):
            task.status = 'succeeded'
        session.commit()

    sss_svc.decrement_pending_video_count(
        11,
        count=3,
        run_id='run-11',
    )

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 11)

    assert state.sync_status == 'success'
    assert state.pending_video_count == 0
    assert state.last_success_at is not None


def test_record_gap_observation_returns_full_backfill_request_when_score_crosses_threshold(
    engine,
    session_factory,
    sss_session_patch,
):
    engine = _setup_state_env(engine)
    sss_svc = subscription_sync_state_service

    now = datetime(2026, 4, 4, 12, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=21,
                subscription_id=7,
                site='youtube.com',
                sync_mode='incremental',
                sync_status='success',
                next_sync_at=now + timedelta(minutes=5),
                last_seen_video_url='https://example.com/video/anchor',
            ),
        )
        session.commit()

    summary = sss_svc.record_gap_observation(
        sync_state_id=21,
        head_sample_urls=['https://example.com/video/new-1', 'https://example.com/video/new-2'],
        anchor_found=False,
        cursor_invalid=True,
        cursor_loop_detected=False,
        total_available=120,
        local_total=80,
        now=now,
    )

    assert summary['gap_suspicion_score'] >= 8
    assert summary['should_request_full'] is True
    assert summary['site'] == 'youtube.com'
    assert summary['sync_state_id'] == 21

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 21)

    assert state.gap_suspicion_score == summary['gap_suspicion_score']
    assert state.head_anchor_missing_count == 1
    assert state.last_full_requested_at is None

    sss_svc.mark_full_sync_requested(21, now=now)

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 21)

    assert state.last_full_requested_at == now


def test_stale_run_cannot_overwrite_newer_sync_state(engine, session_factory, sss_session_patch):
    engine = _setup_state_env(engine)
    now = datetime(2026, 4, 5, 12, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=31,
                subscription_id=3,
                site='youtube',
                sync_mode='incremental',
                sync_status='running',
                cursor_payload={'cursor': 'new'},
                next_sync_at=now,
                queue_token='new-token',
                current_run_id='new-run',
                locked_at=now,
            ),
        )
        session.add_all(
            [
                SubscriptionSyncRun(
                    id='old-run',
                    subscription_id=3,
                    sync_state_id=31,
                    site='youtube',
                    sync_mode='incremental',
                    status='running',
                ),
                SubscriptionSyncRun(
                    id='new-run',
                    subscription_id=3,
                    sync_state_id=31,
                    site='youtube',
                    sync_mode='incremental',
                    status='running',
                ),
            ],
        )
        session.commit()

    result = subscription_sync_state_service.mark_sync_success(
        31,
        cursor_payload={'cursor': 'stale'},
        latest_video_url='https://example.com/stale',
        run_id='old-run',
        queue_token='old-token',
    )

    assert result is None
    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 31)
        old_run = session.get(SubscriptionSyncRun, 'old-run')
    assert state.current_run_id == 'new-run'
    assert state.queue_token == 'new-token'
    assert state.cursor_payload == {'cursor': 'new'}
    assert old_run.status == 'running'


def test_retry_claim_self_heals_running_projection_when_progress_update_was_interrupted(
    engine,
    session_factory,
    sss_session_patch,
):
    engine = _setup_state_env(engine)
    now = datetime(2026, 4, 5, 13, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=32,
                subscription_id=3,
                site='youtube',
                sync_mode='incremental',
                sync_status='running',
                next_sync_at=now,
                queue_token='retry-token',
                current_run_id='retry-run',
                locked_at=now - timedelta(minutes=1),
            ),
        )
        session.add(
            SubscriptionSyncRun(
                id='retry-run',
                subscription_id=3,
                sync_state_id=32,
                site='youtube',
                sync_mode='incremental',
                status='running',
            ),
        )
        session.commit()

    claimed = subscription_sync_state_service.claim_sync_state(
        32,
        'retry-token',
        run_id='retry-run',
        execution_token='direct:retry-run',
    )

    assert claimed is not None
    assert claimed.sync_status == 'running'
    assert claimed.locked_at is not None


def test_terminal_run_id_cannot_be_reused_for_new_execution(engine, session_factory):
    _setup_state_env(engine)
    run_service = SubscriptionSyncRunService(session_factory)
    run_service.create_run(
        subscription_id=3,
        sync_state_id=32,
        site='youtube',
        sync_mode='incremental',
        trigger='manual',
        run_id='terminal-run',
        status='succeeded',
    )

    with pytest.raises(ValueError, match='Terminal sync run cannot be reused'):
        run_service.create_run(
            subscription_id=3,
            sync_state_id=32,
            site='youtube',
            sync_mode='incremental',
            trigger='manual',
            run_id='terminal-run',
            status='queued',
        )


def test_stale_running_recovery_preserves_retry_wait_task(engine, session_factory, sss_session_patch):
    _setup_state_env(engine)
    now = datetime.now()
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=33,
                subscription_id=3,
                site='youtube',
                sync_mode='incremental',
                sync_status='running',
                next_sync_at=now,
                queue_token='retry-token',
                current_run_id='retry-wait-run',
                locked_at=now - timedelta(hours=1),
            ),
        )
        session.add(
            SubscriptionSyncRun(
                id='retry-wait-run',
                subscription_id=3,
                sync_state_id=33,
                site='youtube',
                sync_mode='incremental',
                status='running',
            ),
        )
        job = CrawlJob(job_type='subscription_sync', source_type='scheduled', site='youtube')
        session.add(job)
        session.flush()
        session.add(
            CrawlTask(
                job_id=job.id,
                task_type='subscription_sync_incremental',
                site='youtube',
                sync_state_id=33,
                run_id='retry-wait-run',
                status='retry_wait',
                next_run_at=now + timedelta(minutes=10),
            ),
        )
        session.commit()

    result = subscription_sync_state_service.recover_stale_running_sync_states(timeout=timedelta(minutes=30))

    assert result['recovered'] == 0
    with Session(engine, expire_on_commit=False) as session:
        assert session.get(SubscriptionSyncState, 33).current_run_id == 'retry-wait-run'


def test_enqueue_preflight_does_not_recover_run_with_live_renewed_lease(
    engine,
    session_factory,
    sss_session_patch,
):
    _setup_state_env(engine)
    now = datetime.now()
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=34,
                subscription_id=4,
                site='youtube',
                sync_mode='incremental',
                sync_status='running',
                next_sync_at=now,
                queue_token='live-token',
                current_run_id='live-run',
                locked_at=now - timedelta(hours=1),
            ),
        )
        session.add(
            SubscriptionSyncRun(
                id='live-run',
                subscription_id=4,
                sync_state_id=34,
                site='youtube',
                sync_mode='incremental',
                status='running',
            ),
        )
        job = CrawlJob(job_type='subscription_sync', source_type='scheduled', site='youtube')
        session.add(job)
        session.flush()
        session.add(
            CrawlTask(
                job_id=job.id,
                task_type='subscription_sync_incremental',
                site='youtube',
                sync_state_id=34,
                run_id='live-run',
                status='running',
                lease_until=now + timedelta(minutes=5),
            ),
        )
        session.commit()

    state, status = subscription_sync_state_service.prepare_sync_state_for_enqueue(
        4,
        'https://www.youtube.com/channel/demo',
        'incremental',
        scheduled=False,
    )

    assert status == 'in_progress'
    assert state.current_run_id == 'live-run'


def test_lifecycle_record_gap_observation_enqueues_full_backfill_when_score_crosses_threshold(
    engine,
    session_factory,
    sss_session_patch,
):
    engine = _setup_state_env(engine)

    request_calls = []

    now = datetime(2026, 4, 4, 12, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=22,
                subscription_id=8,
                site='youtube.com',
                sync_mode='incremental',
                sync_status='success',
                next_sync_at=now + timedelta(minutes=5),
                last_seen_video_url='https://example.com/video/anchor',
            ),
        )
        session.commit()

    from domains.subscription.application.services.core.sync.lifecycle import SubscriptionSyncLifecycle
    from domains.subscription.application.services.core.update.models import (
        SubscriptionUpdateRequest,
        SubscriptionUpdateResult,
        UpdateMode,
        UpdateTrigger,
    )

    request = SubscriptionUpdateRequest(
        subscription_id=8,
        sync_state_id=22,
        url='https://www.youtube.com/channel/demo',
        trigger=UpdateTrigger.SCHEDULED,
        mode=UpdateMode.INCREMENTAL,
        trace_id='trace-1',
    )
    result = SubscriptionUpdateResult(
        subscription_id=8,
        success=True,
        videos_found=2,
        videos_enqueued=2,
        head_sample_urls=['https://example.com/video/new-1', 'https://example.com/video/new-2'],
        anchor_found=False,
        cursor_invalid=True,
        cursor_loop_detected=False,
        total_available=120,
    )

    lifecycle = SubscriptionSyncLifecycle(session_factory=session_factory)
    with (
        patch.object(SubscriptionCrudService, 'get_subscription_by_id', return_value=SimpleNamespace(total_videos=80)),
        patch.object(
            SubscriptionSyncLifecycle,
            'request_sync',
            autospec=True,
            side_effect=lambda self, **kw: request_calls.append(kw) or SimpleNamespace(status='queued'),
        ),
    ):
        lifecycle.record_gap_observation(request, result)

    assert request_calls == [
        {
            'subscription_id': 8,
            'url': 'https://www.youtube.com/channel/demo',
            'trigger': UpdateTrigger.SCHEDULED,
            'mode': UpdateMode.FULL,
            'trace_id': 'trace-1',
        }
    ]

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 22)

    assert state.last_full_requested_at is not None


def test_lifecycle_record_gap_observation_skips_full_backfill_when_inflight_budget_exhausted(
    engine,
    session_factory,
    sss_session_patch,
):
    engine = _setup_state_env(engine)

    request_calls = []

    now = datetime(2026, 4, 4, 12, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=23,
                subscription_id=9,
                site='youtube.com',
                sync_mode='incremental',
                sync_status='success',
                next_sync_at=now + timedelta(minutes=5),
                last_seen_video_url='https://example.com/video/anchor',
            ),
        )
        session.commit()

    from domains.subscription.application.services.core.sync.lifecycle import SubscriptionSyncLifecycle
    from domains.subscription.application.services.core.update.models import (
        SubscriptionUpdateRequest,
        SubscriptionUpdateResult,
        UpdateMode,
        UpdateTrigger,
    )

    request = SubscriptionUpdateRequest(
        subscription_id=9,
        sync_state_id=23,
        url='https://www.youtube.com/channel/demo',
        trigger=UpdateTrigger.SCHEDULED,
        mode=UpdateMode.INCREMENTAL,
        trace_id='trace-2',
    )
    result = SubscriptionUpdateResult(
        subscription_id=9,
        success=True,
        videos_found=2,
        videos_enqueued=2,
        head_sample_urls=['https://example.com/video/new-1', 'https://example.com/video/new-2'],
        anchor_found=False,
        cursor_invalid=True,
        cursor_loop_detected=False,
        total_available=120,
    )

    lifecycle = SubscriptionSyncLifecycle(session_factory=session_factory)
    with (
        patch.object(SubscriptionCrudService, 'get_subscription_by_id', return_value=SimpleNamespace(total_videos=80)),
        patch.object(SubscriptionSyncLifecycle, '_can_request_full_sync', return_value=False),
        patch.object(
            SubscriptionSyncLifecycle,
            'request_sync',
            autospec=True,
            side_effect=lambda self, **kw: request_calls.append(kw),
        ),
    ):
        lifecycle.record_gap_observation(request, result)

    assert request_calls == []

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 23)

    assert state.last_full_requested_at is None


def test_expired_feed_execution_cannot_write_before_or_after_task_reclaim(
    engine,
    session_factory,
    sss_session_patch,
):
    _setup_state_env(engine)
    now = datetime.now()
    old_execution_token = 'old-lease-token'
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=41,
                subscription_id=14,
                site='youtube.com',
                sync_mode='incremental',
                sync_status='running',
                cursor_payload={'cursor': 'current'},
                next_sync_at=now,
                queue_token='queue-41',
                current_run_id='run-41',
                execution_token=old_execution_token,
                locked_at=now - timedelta(minutes=1),
            ),
        )
        session.add(
            SubscriptionSyncRun(
                id='run-41',
                subscription_id=14,
                sync_state_id=41,
                site='youtube.com',
                sync_mode='incremental',
                status='running',
            ),
        )
        job = CrawlJob(job_type='subscription_sync', source_type='scheduled', site='youtube.com')
        session.add(job)
        session.flush()
        session.add(
            CrawlTask(
                job_id=job.id,
                task_type='subscription_sync_incremental',
                site='youtube.com',
                subscription_id=14,
                sync_state_id=41,
                run_id='run-41',
                payload={
                    'sync_state_id': 41,
                    'run_id': 'run-41',
                    'queue_token': 'queue-41',
                },
                status='running',
                worker_id='worker-l1',
                lease_token=old_execution_token,
                lease_generation=1,
                lease_until=now - timedelta(seconds=1),
            ),
        )
        session.commit()

    stale_completion = subscription_sync_state_service.mark_sync_success(
        41,
        cursor_payload={'cursor': 'stale-before-reclaim'},
        latest_video_url='https://example.com/stale-before-reclaim',
        run_id='run-41',
        queue_token='queue-41',
        execution_token=old_execution_token,
    )
    stale_gap = subscription_sync_state_service.record_gap_observation(
        41,
        head_sample_urls=['https://example.com/stale'],
        anchor_found=False,
        cursor_invalid=True,
        cursor_loop_detected=False,
        total_available=100,
        local_total=1,
        run_id='run-41',
        execution_token=old_execution_token,
    )
    assert stale_completion is None
    assert stale_gap['sync_state_id'] is None

    crawl_tasks = CrawlTaskService(session_factory=session_factory)
    recovered = crawl_tasks.recover_expired_tasks(now=now, retry_delay_seconds=0)
    assert len(recovered) == 1
    assert recovered[0].execution_token == old_execution_token
    subscription_sync_state_service.reconcile_task_retry_state(
        41,
        'queue-41',
        now=now,
        retryable=True,
        error_message='lease_expired',
        run_id='run-41',
        execution_token=old_execution_token,
    )

    new_task = crawl_tasks.claim_next_task(worker_id='worker-l2', now=now, lease_seconds=60)
    assert new_task is not None
    assert new_task.lease_token != old_execution_token
    assert subscription_sync_state_service.claim_sync_state(
        41,
        'queue-41',
        run_id='run-41',
        execution_token=new_task.lease_token,
    ) is not None

    assert subscription_sync_state_service.mark_sync_success(
        41,
        cursor_payload={'cursor': 'stale-after-reclaim'},
        latest_video_url='https://example.com/stale-after-reclaim',
        run_id='run-41',
        queue_token='queue-41',
        execution_token=old_execution_token,
    ) is None
    assert subscription_sync_state_service.record_gap_observation(
        41,
        head_sample_urls=['https://example.com/stale-again'],
        anchor_found=False,
        cursor_invalid=True,
        cursor_loop_detected=False,
        total_available=100,
        local_total=1,
        run_id='run-41',
        execution_token=old_execution_token,
    )['sync_state_id'] is None

    video_tasks = VideoExtractionTaskService(
        get_video_by_url=lambda _url: None,
        crawl_tasks=crawl_tasks,
    )
    with (
        patch(
            'domains.video.application.services.extraction.task_service.SiteCatalog.is_site_enabled',
            return_value=True,
        ),
        pytest.raises(CrawlTaskStateError, match='Stale video extraction parent'),
    ):
        video_tasks.enqueue(
            VideoExtractDto(
                url='https://www.youtube.com/watch?v=stale',
                subscribed=True,
                subscription_id=14,
                sync_state_id=41,
                run_id='run-41',
                parent_execution_token=old_execution_token,
                only_extract=True,
            ),
        )

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 41)
        video_task_count = session.query(CrawlTask).filter(CrawlTask.task_type == 'video_extract').count()
    assert state.execution_token == new_task.lease_token
    assert state.cursor_payload == {'cursor': 'current'}
    assert state.gap_suspicion_score == 0
    assert video_task_count == 0
