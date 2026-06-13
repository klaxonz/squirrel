from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

import subscription.services.core.sync.state.service as subscription_sync_state_service
from shared_kernel.domain.base import Base
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.crawl_job import CrawlJob
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.subscription.domain.models.outbox_event import OutboxEvent
from domains.subscription.domain.models.subscription import Subscription
from domains.subscription.domain.models.subscription_sync_event import SubscriptionSyncEvent
from domains.subscription.domain.models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState
from domains.subscription.domain.models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from domains.subscription.schemas.dto.sync_dashboard_dto import SyncDashboardItemDto
from domains.subscription.application.services.core.sync.dashboard_service import SubscriptionSyncDashboardService
from domains.subscription.application.services.core.sync.progress import subscription_sync_progress
from domains.subscription.application.services.sync.items import SyncDashboardItemFactory
from domains.subscription.application.services.sync.presentation import sort_items
from domains.subscription.application.services.sync.site_icons import SiteIconResolver


@pytest.fixture
def engine(engine):
    return engine


@pytest.fixture
def sss_session_patch(session_factory):
    """Replacement for sss_session fixture using patch instead of monkeypatch."""
    import subscription.services.core.sync.projection.store as projection_store
    from infrastructure.database import session as database
    from domains.subscription.application.services.core.sync.projection.service import subscription_sync_projection_service
    from domains.subscription.application.services.core.sync.run_service import subscription_sync_run_service

    with patch.object(database, 'get_session', session_factory), \
         patch.object(subscription_sync_run_service, 'next_seq_no', lambda stream_id, *, session=None: 1), \
         patch.object(projection_store, 'advisory_lock', lambda session, key: None), \
         patch.object(subscription_sync_projection_service, 'apply_event', lambda event, session=None: event):
        yield


def _setup_projection_env(engine):
    Base.metadata.create_all(
        engine,
        tables=[
            CrawlTask.__table__,
            Subscription.__table__,
            UserSubscription.__table__,
            SubscriptionSyncEvent.__table__,
            SubscriptionSyncRunProjection.__table__,
            SubscriptionSyncSubscriptionProjection.__table__,
        ],
    )
    return engine


def _setup_state_env(engine):
    Base.metadata.create_all(
        engine,
        tables=[
            SubscriptionSyncEvent.__table__,
            SubscriptionSyncState.__table__,
            OutboxEvent.__table__,
        ],
    )
    return engine


def _setup_projection_reconcile_env(engine):
    Base.metadata.create_all(
        engine,
        tables=[
            CrawlJob.__table__,
            CrawlTask.__table__,
            SubscriptionSyncEvent.__table__,
            SubscriptionSyncState.__table__,
            SubscriptionSyncRunProjection.__table__,
            SubscriptionSyncSubscriptionProjection.__table__,
        ],
    )
    return engine


def _seed_projection_data(engine):
    now = datetime(2026, 4, 2, 11, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Subscription(
                id=1,
                type="CHANNEL",
                name="Running Channel",
                url="https://www.youtube.com/channel/running",
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=now,
                updated_at=now,
            ),
            Subscription(
                id=4,
                type="CHANNEL",
                name="Running Earlier",
                url="https://www.youtube.com/channel/earlier",
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=now,
                updated_at=now,
            ),
            Subscription(
                id=2,
                type="CHANNEL",
                name="Queued First",
                url="https://space.bilibili.com/queued-1",
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=now,
                updated_at=now,
            ),
            Subscription(
                id=3,
                type="CHANNEL",
                name="Queued Second",
                url="https://space.bilibili.com/queued-2",
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=now,
                updated_at=now,
            ),
        ])
        session.add_all([
            UserSubscription(id=1, user_id=1, subscription_id=1, is_deleted=False, is_nsfw=False, created_at=now, updated_at=now),
            UserSubscription(id=4, user_id=1, subscription_id=4, is_deleted=False, is_nsfw=False, created_at=now, updated_at=now),
            UserSubscription(id=2, user_id=1, subscription_id=2, is_deleted=False, is_nsfw=False, created_at=now, updated_at=now),
            UserSubscription(id=3, user_id=1, subscription_id=3, is_deleted=False, is_nsfw=False, created_at=now, updated_at=now),
        ])
        session.add_all([
            SubscriptionSyncRunProjection(
                run_id="run-running-earlier",
                subscription_id=4,
                sync_state_id=104,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-running-earlier",
                trace_id="trace-running-earlier",
                status="running",
                current_phase="fetching_feed",
                queued_at=now - timedelta(minutes=6),
                started_at=now - timedelta(minutes=5),
                finished_at=None,
                duration_ms=0,
                failure_count=0,
                error_type=None,
                error_message=None,
                videos_found=2,
                videos_enqueued=0,
                videos_extracted=0,
                videos_skipped=0,
                pending_video_count=0,
                last_event_seq_no=7,
                last_event_at=now - timedelta(minutes=1),
                created_at=now - timedelta(minutes=6),
                updated_at=now - timedelta(minutes=1),
            ),
            SubscriptionSyncRunProjection(
                run_id="run-running",
                subscription_id=1,
                sync_state_id=101,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-running",
                trace_id="trace-running",
                status="running",
                current_phase="extracting",
                queued_at=now - timedelta(minutes=3),
                started_at=now - timedelta(minutes=2),
                finished_at=None,
                duration_ms=0,
                failure_count=0,
                error_type=None,
                error_message=None,
                videos_found=10,
                videos_enqueued=8,
                videos_extracted=5,
                videos_skipped=2,
                pending_video_count=3,
                last_event_seq_no=8,
                last_event_at=now,
                created_at=now - timedelta(minutes=3),
                updated_at=now,
            ),
            SubscriptionSyncRunProjection(
                run_id="run-queued-1",
                subscription_id=2,
                sync_state_id=102,
                site="bilibili.com",
                sync_mode="incremental",
                trigger="scheduled",
                request_id="req-queued-1",
                trace_id="trace-queued-1",
                status="queued",
                current_phase="queued",
                queued_at=now - timedelta(minutes=4),
                started_at=None,
                finished_at=None,
                duration_ms=0,
                failure_count=0,
                error_type=None,
                error_message=None,
                videos_found=0,
                videos_enqueued=0,
                videos_extracted=0,
                videos_skipped=0,
                pending_video_count=0,
                last_event_seq_no=2,
                last_event_at=now - timedelta(minutes=4),
                created_at=now - timedelta(minutes=4),
                updated_at=now - timedelta(minutes=4),
            ),
            SubscriptionSyncRunProjection(
                run_id="run-queued-2",
                subscription_id=3,
                sync_state_id=103,
                site="bilibili.com",
                sync_mode="full",
                trigger="scheduled",
                request_id="req-queued-2",
                trace_id="trace-queued-2",
                status="queued",
                current_phase="queued",
                queued_at=now - timedelta(minutes=1),
                started_at=None,
                finished_at=None,
                duration_ms=0,
                failure_count=0,
                error_type=None,
                error_message=None,
                videos_found=0,
                videos_enqueued=0,
                videos_extracted=0,
                videos_skipped=0,
                pending_video_count=0,
                last_event_seq_no=2,
                last_event_at=now - timedelta(minutes=1),
                created_at=now - timedelta(minutes=1),
                updated_at=now - timedelta(minutes=1),
            ),
        ])
        session.add_all([
            SubscriptionSyncSubscriptionProjection(
                subscription_id=4,
                latest_run_id="run-running-earlier",
                current_status="running",
                current_phase="fetching_feed",
                last_sync_at=now - timedelta(minutes=5),
                last_success_at=None,
                next_sync_at=now + timedelta(minutes=8),
                last_error_message=None,
                pending_video_count=0,
                failure_streak=0,
                last_event_seq_no=7,
                updated_at=now - timedelta(minutes=1),
            ),
            SubscriptionSyncSubscriptionProjection(
                subscription_id=1,
                latest_run_id="run-running",
                current_status="running",
                current_phase="extracting",
                last_sync_at=now - timedelta(minutes=2),
                last_success_at=None,
                next_sync_at=now + timedelta(minutes=10),
                last_error_message=None,
                pending_video_count=3,
                failure_streak=0,
                last_event_seq_no=8,
                updated_at=now,
            ),
            SubscriptionSyncSubscriptionProjection(
                subscription_id=2,
                latest_run_id="run-queued-1",
                current_status="queued",
                current_phase="queued",
                last_sync_at=now - timedelta(hours=1),
                last_success_at=now - timedelta(hours=1),
                next_sync_at=now,
                last_error_message=None,
                pending_video_count=0,
                failure_streak=0,
                last_event_seq_no=2,
                updated_at=now - timedelta(minutes=4),
            ),
            SubscriptionSyncSubscriptionProjection(
                subscription_id=3,
                latest_run_id="run-queued-2",
                current_status="queued",
                current_phase="queued",
                last_sync_at=now - timedelta(hours=2),
                last_success_at=now - timedelta(hours=2),
                next_sync_at=now,
                last_error_message=None,
                pending_video_count=0,
                failure_streak=0,
                last_event_seq_no=2,
                updated_at=now - timedelta(minutes=1),
            ),
        ])
        session.commit()


def test_sync_dashboard_feed_dashboard_snapshot_uses_one_consistent_result_shape(engine, session_factory):
    engine = _setup_projection_env(engine)
    _seed_projection_data(engine)
    catalog = {
        "youtube.com": {"icon_url": "/api/sites/youtube/icon"},
        "bilibili.com": {"icon_url": "/api/sites/bilibili/icon"},
    }
    svc = SubscriptionSyncDashboardService(
        session_factory=session_factory,
        item_factory=SyncDashboardItemFactory(
            progress_service=subscription_sync_progress,
            site_icon_resolver=SiteIconResolver(lambda: catalog),
        ),
    )

    snapshot = svc.get_feed_dashboard_snapshot(
        user_id=1,
        site=None,
        query=None,
        date_from="2026-04-02T00:00:00",
        date_to="2026-04-03T00:00:00",
    )

    assert snapshot["overview"].running_count == 1
    assert snapshot["overview"].awaiting_extract_count == 1
    assert [item.subscription_name for item in snapshot["runningPreview"]] == ["Running Earlier"]
    assert [item.subscription_name for item in snapshot["queuedPreview"]] == ["Queued First", "Queued Second"]
    assert snapshot["runningPreview"][0].site_icon_url == "/api/sites/youtube/icon"
    assert [item.site_icon_url for item in snapshot["queuedPreview"]] == [
        "/api/sites/bilibili/icon",
        "/api/sites/bilibili/icon",
    ]
    assert [run["run_id"] for run in snapshot["recentRuns"]] == ["run-running"]

    assert "recentlyCompletedRuns" in snapshot
    assert len(snapshot["recentlyCompletedRuns"]) > 0
    first_call_run_ids = {run["run_id"] for run in snapshot["recentlyCompletedRuns"]}

    snapshot2 = svc.get_feed_dashboard_snapshot(
        user_id=1,
        site=None,
        query=None,
        date_from="2026-04-02T00:00:00",
        date_to="2026-04-03T00:00:00",
    )
    second_call_new_ids = {run["run_id"] for run in snapshot2["recentlyCompletedRuns"]}
    assert len(second_call_new_ids) == 0 or not first_call_run_ids.issubset(second_call_new_ids)


def test_sync_dashboard_feed_dashboard_snapshot_does_not_trim_running_or_queued_items(engine, session_factory):
    engine = _setup_projection_env(engine)
    _seed_projection_data(engine)
    svc = SubscriptionSyncDashboardService(session_factory=session_factory)

    with patch("services.subscription.sync.dashboard_service.SYNC_DASHBOARD_PREVIEW_LIMIT", 1):
        with Session(engine, expire_on_commit=False) as session:
            run_projection = session.get(SubscriptionSyncRunProjection, "run-running")
            run_projection.current_phase = "fetching_feed"
            run_projection.pending_video_count = 0

            subscription_projection = session.get(SubscriptionSyncSubscriptionProjection, 1)
            subscription_projection.current_phase = "fetching_feed"
            subscription_projection.pending_video_count = 0
            session.commit()

        snapshot = svc.get_feed_dashboard_snapshot(
            user_id=1,
            site=None,
            query=None,
            date_from="2026-04-02T00:00:00",
            date_to="2026-04-03T00:00:00",
        )

    assert [item.subscription_name for item in snapshot["runningPreview"]] == ["Running Earlier", "Running Channel"]
    assert [item.subscription_name for item in snapshot["queuedPreview"]] == ["Queued First", "Queued Second"]


def test_sync_dashboard_feed_dashboard_snapshot_reuses_site_catalog_for_icon_resolution(engine, session_factory):
    engine = _setup_projection_env(engine)
    _seed_projection_data(engine)

    calls = []

    def _fake_get_cached_site_catalog():
        calls.append(1)
        return {
            "youtube.com": {
                "icon_url": "/api/sites/youtube/icon",
            },
            "bilibili.com": {
                "icon_url": "/api/sites/bilibili/icon",
            },
        }

    svc = SubscriptionSyncDashboardService(
        session_factory=session_factory,
        item_factory=SyncDashboardItemFactory(
            progress_service=subscription_sync_progress,
            site_icon_resolver=SiteIconResolver(_fake_get_cached_site_catalog),
        ),
    )

    snapshot = svc.get_feed_dashboard_snapshot(
        user_id=1,
        site=None,
        query=None,
        date_from="2026-04-02T00:00:00",
        date_to="2026-04-03T00:00:00",
    )

    assert snapshot["runningPreview"][0].site_icon_url == "/api/sites/youtube/icon"
    assert snapshot["queuedPreview"][0].site_icon_url == "/api/sites/bilibili/icon"
    assert snapshot["recentRuns"][0]["site_icon_url"] == "/api/sites/youtube/icon"
    assert len(calls) == 2


def test_sort_items_accepts_mixed_queued_rank_sources():
    items = [
        SyncDashboardItemDto(
            subscription_id=1,
            subscription_name="Candidate Ranked",
            display_status="queued",
            queued_at="2026-04-02 10:00:00",
        ),
        SyncDashboardItemDto(
            subscription_id=2,
            subscription_name="Projection Fallback",
            display_status="queued",
            queued_at="2026-04-02 09:30:00",
        ),
        SyncDashboardItemDto(
            subscription_id=3,
            subscription_name="Backlog Ranked",
            display_status="queued",
            queued_at="2026-04-02 09:45:00",
        ),
    ]

    result = sort_items(
        items,
        "queued",
        queued_candidate_rank_map={1: 1},
        queued_backlog_rank_map={3: 2},
    )

    assert [item.subscription_id for item in result] == [1, 3, 2]


def test_reconcile_retry_wait_run_projections_emits_queued_event_for_stale_feed_run(engine, session_factory, sss_session_patch):
    engine = _setup_projection_reconcile_env(engine)
    sss_svc = subscription_sync_state_service
    captured_events = []

    with patch(
        "services.subscription.sync.state._events.append_event",
        lambda event_input, session=None, project=True: captured_events.append(event_input) or event_input,
    ):

        now = datetime(2026, 4, 2, 22, 24, 19)
        with Session(engine, expire_on_commit=False) as session:
            session.add(
                CrawlJob(
                    id=1,
                    job_type="subscription_sync",
                    source_type="scheduled",
                    site="bilibili.com",
                    subscription_id=112,
                    status="running",
                    payload={},
                    created_at=now - timedelta(minutes=1),
                    updated_at=now - timedelta(minutes=1),
                ),
            )
            session.add(
                SubscriptionSyncState(
                    id=1334,
                    subscription_id=112,
                    site="bilibili.com",
                    sync_mode="full",
                    sync_status="queued",
                    cursor_payload={"page": 5},
                    last_seen_video_url="https://www.bilibili.com/video/demo",
                    last_sync_at=now - timedelta(minutes=1),
                    last_success_at=now - timedelta(hours=1),
                    next_sync_at=now + timedelta(minutes=1),
                    queued_at=now,
                    locked_at=None,
                    queue_token="queue-token-1",
                    pending_video_count=0,
                    failure_count=1,
                    version=10,
                    last_error="lease_expired",
                    created_at=now - timedelta(days=1),
                    updated_at=now,
                    idle_sync_count=0,
                ),
            )
            session.add(
                SubscriptionSyncRunProjection(
                    run_id="run-stale-1",
                    subscription_id=112,
                    sync_state_id=1334,
                    site="bilibili.com",
                    sync_mode="full",
                    trigger="scheduled",
                    request_id="req-stale-1",
                    trace_id="trace-stale-1",
                    status="running",
                    current_phase="fetching_feed",
                    queued_at=now - timedelta(minutes=2),
                    started_at=now - timedelta(minutes=1),
                    finished_at=None,
                    duration_ms=0,
                    failure_count=0,
                    error_type=None,
                    error_message=None,
                    videos_found=50,
                    videos_enqueued=0,
                    videos_extracted=0,
                    videos_skipped=25,
                    pending_video_count=0,
                    last_event_seq_no=12,
                    last_event_at=now - timedelta(seconds=59),
                    created_at=now - timedelta(minutes=2),
                    updated_at=now - timedelta(seconds=59),
                ),
            )
            session.add(
                SubscriptionSyncSubscriptionProjection(
                    subscription_id=112,
                    latest_run_id="run-stale-1",
                    current_status="running",
                    current_phase="fetching_feed",
                    last_sync_at=now - timedelta(hours=1),
                    last_success_at=now - timedelta(hours=1),
                    next_sync_at=now - timedelta(minutes=1),
                    last_error_message=None,
                    pending_video_count=0,
                    failure_streak=0,
                    last_event_seq_no=12,
                    updated_at=now - timedelta(seconds=59),
                ),
            )
            session.add(
                CrawlTask(
                    id=6877,
                    job_id=1,
                    task_type="subscription_sync_full",
                    site="bilibili.com",
                    subscription_id=112,
                    status="retry_wait",
                    worker_id=None,
                    attempt=1,
                    max_attempts=3,
                    next_run_at=now + timedelta(seconds=30),
                    lease_until=None,
                    last_error="lease_expired",
                    last_error_type="lease_expired",
                    trace_id="trace-stale-1",
                    payload={
                        "subscription_id": 112,
                        "sync_state_id": 1334,
                        "mode": "full",
                        "queue_token": "queue-token-1",
                        "trigger": "scheduled",
                        "run_id": "run-stale-1",
                        "request_id": "req-stale-1",
                        "trace_id": "trace-stale-1",
                    },
                    created_at=now - timedelta(minutes=2),
                    updated_at=now,
                    started_at=now - timedelta(minutes=1),
                    finished_at=None,
                ),
            )
            session.commit()

        result = sss_svc.reconcile_retry_wait_run_projections()

        assert result == {"candidates": 1, "repaired": 1}
        assert len(captured_events) == 1
        assert captured_events[0].stream_id == "run-stale-1"
        assert captured_events[0].event_type == "queued"
        assert captured_events[0].event_phase == "queued"
        assert captured_events[0].event_status == "queued"
        assert captured_events[0].request_id == "req-stale-1"
        assert captured_events[0].trace_id == "trace-stale-1"
        assert captured_events[0].trigger == "scheduled"
        assert captured_events[0].message == "lease_expired"
        assert captured_events[0].payload["queue_token"] == "queue-token-1"


def test_mark_sync_success_stays_running_until_pending_videos_are_drained(engine, session_factory, sss_session_patch):
    engine = _setup_state_env(engine)
    sss_svc = subscription_sync_state_service
    captured_events = []

    with patch(
        "services.subscription.sync.state._events.append_event",
        lambda event_input, session=None, project=True: captured_events.append(event_input) or event_input,
    ):

        now = datetime(2026, 4, 2, 12, 0, 0)
        with Session(engine, expire_on_commit=False) as session:
            session.add(
                SubscriptionSyncState(
                    id=11,
                    subscription_id=1,
                    site="youtube.com",
                    sync_mode="incremental",
                    sync_status="running",
                    cursor_payload={"cursor": "done"},
                    last_seen_video_url="https://example.com/video/1",
                    last_sync_at=now - timedelta(minutes=1),
                    last_success_at=None,
                    next_sync_at=now + timedelta(minutes=5),
                    queued_at=now - timedelta(minutes=2),
                    locked_at=now - timedelta(minutes=2),
                    queue_token="queue-token",
                    pending_video_count=3,
                    failure_count=0,
                    idle_sync_count=0,
                    version=0,
                    last_error=None,
                    created_at=now - timedelta(hours=1),
                    updated_at=now - timedelta(minutes=2),
                ),
            )
            session.commit()

        sss_svc.mark_sync_success(
            11,
            cursor_payload={"cursor": "done"},
            latest_video_url="https://example.com/video/1",
            source_video_count=10,
            videos_found=10,
            videos_enqueued=8,
            run_id="run-1",
            request_id="req-1",
            trace_id="trace-1",
            trigger="manual",
        )

        with Session(engine, expire_on_commit=False) as session:
            state = session.get(SubscriptionSyncState, 11)

        assert state.sync_status == "running"
        assert state.locked_at is None
        assert state.pending_video_count == 3
        assert state.last_success_at is None
        assert [event.event_type for event in captured_events] == ["phase_changed"]
        assert captured_events[-1].event_phase == "extracting"

        sss_svc.decrement_pending_video_count(
            11,
            count=3,
            run_id="run-1",
            request_id="req-1",
            trace_id="trace-1",
            trigger="manual",
        )

        with Session(engine, expire_on_commit=False) as session:
            state = session.get(SubscriptionSyncState, 11)

        assert state.sync_status == "success"
        assert state.pending_video_count == 0
        assert state.last_success_at is not None
        assert [event.event_type for event in captured_events] == ["phase_changed", "completed"]


def test_reconcile_terminal_drained_sync_states_completes_original_latest_run(engine, session_factory, sss_session_patch):
    engine = _setup_projection_reconcile_env(engine)
    sss_svc = subscription_sync_state_service
    captured_events = []

    with patch(
        "services.subscription.sync.state._events.append_event",
        lambda event_input, session=None, project=True: captured_events.append(event_input) or event_input,
    ), \
         patch(
             "services.subscription.sync.state._recovery.crawl_task_service.summarize_video_task_states_by_sync_state",
             dict,
         ):

        now = datetime(2026, 4, 2, 12, 0, 0)
        with Session(engine, expire_on_commit=False) as session:
            session.add(
                SubscriptionSyncState(
                    id=11,
                    subscription_id=1,
                    site="youtube.com",
                    sync_mode="incremental",
                    sync_status="running",
                    cursor_payload={"cursor": "done"},
                    last_seen_video_url="https://example.com/video/1",
                    last_sync_at=now - timedelta(minutes=1),
                    last_success_at=None,
                    next_sync_at=now + timedelta(minutes=5),
                    queued_at=None,
                    locked_at=None,
                    queue_token=None,
                    pending_video_count=1,
                    failure_count=0,
                    idle_sync_count=0,
                    version=0,
                    last_error=None,
                    created_at=now - timedelta(hours=1),
                    updated_at=now - timedelta(minutes=2),
                ),
            )
            session.add(
                SubscriptionSyncRunProjection(
                    run_id="run-original",
                    subscription_id=1,
                    sync_state_id=11,
                    site="youtube.com",
                    sync_mode="incremental",
                    trigger="manual",
                    request_id="req-original",
                    trace_id="trace-original",
                    status="running",
                    current_phase="extracting",
                    pending_video_count=1,
                    last_event_seq_no=4,
                    last_event_at=now - timedelta(seconds=30),
                    started_at=now - timedelta(minutes=1),
                    created_at=now - timedelta(minutes=2),
                    updated_at=now - timedelta(seconds=30),
                ),
            )
            session.add(
                SubscriptionSyncSubscriptionProjection(
                    subscription_id=1,
                    latest_run_id="run-original",
                    current_status="running",
                    current_phase="extracting",
                    pending_video_count=1,
                    last_event_seq_no=4,
                    updated_at=now - timedelta(seconds=30),
                ),
            )
            session.commit()

        result = sss_svc.reconcile_terminal_drained_sync_states()

    assert result == {"running_states": 1, "completed": 1, "failed": 0}
    assert [(event.stream_id, event.event_type, event.event_phase, event.event_status) for event in captured_events] == [
        ("run-original", "completed", "completed", "success"),
    ]


def test_record_gap_observation_emits_full_backfill_request_when_score_crosses_threshold(engine, session_factory, sss_session_patch):
    engine = _setup_state_env(engine)
    sss_svc = subscription_sync_state_service

    now = datetime(2026, 4, 4, 12, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=21,
                subscription_id=7,
                site="youtube.com",
                sync_mode="incremental",
                sync_status="success",
                next_sync_at=now + timedelta(minutes=5),
                last_seen_video_url="https://example.com/video/anchor",
            ),
        )
        session.commit()

    summary = sss_svc.record_gap_observation(
        sync_state_id=21,
        head_sample_urls=["https://example.com/video/new-1", "https://example.com/video/new-2"],
        anchor_found=False,
        cursor_invalid=True,
        cursor_loop_detected=False,
        total_available=120,
        local_total=80,
        now=now,
    )

    assert summary["gap_suspicion_score"] >= 8

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 21)
        events = session.query(OutboxEvent).all()

    assert state.gap_suspicion_score == summary["gap_suspicion_score"]
    assert state.head_anchor_missing_count == 1
    assert len(events) == 1
    assert events[0].event_type == "full_backfill_requested"
    assert events[0].payload["subscription_id"] == 7
