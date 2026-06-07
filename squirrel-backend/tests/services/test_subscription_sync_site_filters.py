from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from models import Base
from models.crawl_job import CrawlJob
from models.crawl_task import CrawlTask
from models.links import UserSubscription
from models.subscription import Subscription
from models.subscription_sync_event import SubscriptionSyncEvent
from models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from services.subscription_sync_center_service import SubscriptionSyncCenterService
from services.subscription_sync_history_service import SubscriptionSyncHistoryService
from utils.site_catalog import SiteCatalog


@pytest.fixture
def engine(engine):
    Base.metadata.create_all(
        engine,
        tables=[
            CrawlJob.__table__,
            CrawlTask.__table__,
            Subscription.__table__,
            UserSubscription.__table__,
            SubscriptionSyncEvent.__table__,
            SubscriptionSyncRunProjection.__table__,
            SubscriptionSyncSubscriptionProjection.__table__,
        ],
    )
    return engine


@pytest.fixture
def svc(session_factory):
    return SubscriptionSyncCenterService(session_factory=session_factory)


@pytest.fixture
def history_svc(session_factory):
    return SubscriptionSyncHistoryService(session_factory=session_factory)


def _setup_test_env(engine, monkeypatch):
    monkeypatch.setattr(
        SubscriptionSyncCenterService,
        "_refresh_runtime_sync_health",
        lambda self, force=False: None,
    )
    monkeypatch.setattr(
        SiteCatalog,
        "resolve_domains",
        classmethod(lambda cls, key: ["youtube.com", "youtu.be"] if key == "youtube" else []),
    )
    monkeypatch.setattr(
        SiteCatalog,
        "find_site_by_domain",
        classmethod(lambda cls, domain: ("youtube", {}) if domain == "youtube.com" else (None, None)),
    )
    monkeypatch.setattr(
        SiteCatalog,
        "get_catalog",
        classmethod(
            lambda cls: {
                "youtube": {
                    "domains": ["youtube.com", "youtu.be"],
                    "icon_url": "/api/sites/youtube/icon",
                },
            },
        ),
    )
    return engine


def _seed_sync_projection(engine):
    with Session(engine, expire_on_commit=False) as session:
        subscription = Subscription(
            id=1,
            type="CHANNEL",
            name="YouTube Channel",
            url="https://www.youtube.com/channel/demo",
            avatar=None,
            description=None,
            total_videos=0,
            is_deleted=False,
            extra_data={},
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )
        session.add(subscription)
        session.add(
            UserSubscription(
                id=1,
                user_id=1,
                subscription_id=1,
                is_deleted=False,
                is_nsfw=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
        )
        session.add(
            SubscriptionSyncRunProjection(
                run_id="run-1",
                subscription_id=1,
                sync_state_id=1,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-1",
                trace_id="trace-1",
                status="success",
                current_phase="completed",
                queued_at=datetime(2024, 1, 1, 1, 0, 0),
                started_at=datetime(2024, 1, 1, 1, 1, 0),
                finished_at=datetime(2024, 1, 1, 1, 2, 0),
                duration_ms=60000,
                failure_count=0,
                error_type=None,
                error_message=None,
                videos_found=3,
                videos_enqueued=2,
                videos_extracted=2,
                videos_skipped=1,
                pending_video_count=0,
                last_event_seq_no=4,
                last_event_at=datetime(2024, 1, 1, 1, 2, 0),
                created_at=datetime(2024, 1, 1, 1, 0, 0),
                updated_at=datetime(2024, 1, 1, 1, 2, 0),
            ),
        )
        session.add(
            SubscriptionSyncSubscriptionProjection(
                subscription_id=1,
                latest_run_id="run-1",
                current_status="success",
                current_phase="completed",
                last_sync_at=datetime(2024, 1, 1, 1, 2, 0),
                last_success_at=datetime(2024, 1, 1, 1, 2, 0),
                next_sync_at=datetime(2024, 1, 1, 2, 0, 0),
                last_error_message=None,
                pending_video_count=0,
                failure_streak=0,
                last_event_seq_no=4,
                updated_at=datetime(2024, 1, 1, 1, 2, 0),
            ),
        )
        session.commit()


def test_list_runs_accepts_site_slug_when_projection_stores_domain(engine, session_factory, monkeypatch):
    engine = _setup_test_env(engine, monkeypatch)
    _seed_sync_projection(engine)
    history_svc = SubscriptionSyncHistoryService(session_factory=session_factory)

    result = history_svc.list_runs(user_id=1, site="youtube", page=1, page_size=20)

    assert result["total"] == 1
    assert [item["site"] for item in result["data"]] == ["youtube.com"]
    assert [item["site_icon_url"] for item in result["data"]] == ["/api/sites/youtube/icon"]


def test_list_runs_recent_excludes_running_and_queued_statuses(engine, session_factory, monkeypatch):
    engine = _setup_test_env(engine, monkeypatch)
    _seed_sync_projection(engine)
    history_svc = SubscriptionSyncHistoryService(session_factory=session_factory)

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            SubscriptionSyncRunProjection(
                run_id="run-2",
                subscription_id=1,
                sync_state_id=1,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-2",
                trace_id="trace-2",
                status="queued",
                current_phase="queued",
                queued_at=datetime(2024, 1, 1, 1, 3, 0),
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
                last_event_seq_no=1,
                last_event_at=datetime(2024, 1, 1, 1, 3, 0),
                created_at=datetime(2024, 1, 1, 1, 3, 0),
                updated_at=datetime(2024, 1, 1, 1, 3, 0),
            ),
            SubscriptionSyncRunProjection(
                run_id="run-3",
                subscription_id=1,
                sync_state_id=1,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-3",
                trace_id="trace-3",
                status="running",
                current_phase="fetching_feed",
                queued_at=datetime(2024, 1, 1, 1, 4, 0),
                started_at=datetime(2024, 1, 1, 1, 4, 5),
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
                last_event_at=datetime(2024, 1, 1, 1, 4, 5),
                created_at=datetime(2024, 1, 1, 1, 4, 0),
                updated_at=datetime(2024, 1, 1, 1, 4, 5),
            ),
        ])
        session.commit()

    result = history_svc.list_runs(user_id=1, status="recent", page=1, page_size=20)

    assert result["total"] == 1
    assert [item["run_id"] for item in result["data"]] == ["run-1"]


def test_list_runs_feed_recent_includes_handoff_and_terminal_runs(engine, session_factory, monkeypatch):
    engine = _setup_test_env(engine, monkeypatch)
    _seed_sync_projection(engine)
    history_svc = SubscriptionSyncHistoryService(session_factory=session_factory)

    with Session(engine, expire_on_commit=False) as session:
        session.add(
            Subscription(
                id=2,
                type="CHANNEL",
                name="Second YouTube Channel",
                url="https://www.youtube.com/channel/demo-2",
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
        )
        session.add(
            UserSubscription(
                id=2,
                user_id=1,
                subscription_id=2,
                is_deleted=False,
                is_nsfw=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
        )
        session.add_all([
            SubscriptionSyncRunProjection(
                run_id="run-2",
                subscription_id=1,
                sync_state_id=1,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-2",
                trace_id="trace-2",
                status="queued",
                current_phase="queued",
                queued_at=datetime(2024, 1, 1, 1, 3, 0),
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
                last_event_seq_no=1,
                last_event_at=datetime(2024, 1, 1, 1, 3, 0),
                created_at=datetime(2024, 1, 1, 1, 3, 0),
                updated_at=datetime(2024, 1, 1, 1, 3, 0),
            ),
            SubscriptionSyncRunProjection(
                run_id="run-3",
                subscription_id=1,
                sync_state_id=1,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-3",
                trace_id="trace-3",
                status="running",
                current_phase="fetching_feed",
                queued_at=datetime(2024, 1, 1, 1, 4, 0),
                started_at=datetime(2024, 1, 1, 1, 4, 5),
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
                last_event_at=datetime(2024, 1, 1, 1, 4, 5),
                created_at=datetime(2024, 1, 1, 1, 4, 0),
                updated_at=datetime(2024, 1, 1, 1, 4, 5),
            ),
            SubscriptionSyncRunProjection(
                run_id="run-4",
                subscription_id=2,
                sync_state_id=2,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-4",
                trace_id="trace-4",
                status="running",
                current_phase="extracting",
                queued_at=datetime(2024, 1, 1, 1, 5, 0),
                started_at=datetime(2024, 1, 1, 1, 5, 5),
                finished_at=None,
                duration_ms=0,
                failure_count=0,
                error_type=None,
                error_message=None,
                videos_found=4,
                videos_enqueued=4,
                videos_extracted=1,
                videos_skipped=0,
                pending_video_count=3,
                last_event_seq_no=3,
                last_event_at=datetime(2024, 1, 1, 1, 5, 6),
                created_at=datetime(2024, 1, 1, 1, 5, 0),
                updated_at=datetime(2024, 1, 1, 1, 5, 6),
            ),
            SubscriptionSyncSubscriptionProjection(
                subscription_id=2,
                latest_run_id="run-4",
                current_status="running",
                current_phase="extracting",
                last_sync_at=datetime(2024, 1, 1, 1, 5, 5),
                last_success_at=None,
                next_sync_at=datetime(2024, 1, 1, 2, 5, 0),
                last_error_message=None,
                pending_video_count=3,
                failure_streak=0,
                last_event_seq_no=3,
                updated_at=datetime(2024, 1, 1, 1, 5, 6),
            ),
        ])
        session.commit()

    result = history_svc.list_runs(user_id=1, status="feed_recent", page=1, page_size=20)

    assert result["total"] == 2
    assert [item["run_id"] for item in result["data"]] == ["run-4", "run-1"]
    assert result["data"][0]["feed_completed"] is True
    assert result["data"][0]["status"] == "running"
    assert result["data"][0]["current_phase"] == "extracting"


def test_list_runs_feed_recent_sorts_by_feed_completion_time_not_last_event(engine, session_factory, monkeypatch):
    engine = _setup_test_env(engine, monkeypatch)
    _seed_sync_projection(engine)
    history_svc = SubscriptionSyncHistoryService(session_factory=session_factory)

    with Session(engine, expire_on_commit=False) as session:
        session.add(
            Subscription(
                id=2,
                type="CHANNEL",
                name="Second YouTube Channel",
                url="https://www.youtube.com/channel/demo-2",
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
        )
        session.add(
            UserSubscription(
                id=2,
                user_id=1,
                subscription_id=2,
                is_deleted=False,
                is_nsfw=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
        )
        run_one = session.get(SubscriptionSyncRunProjection, "run-1")
        assert run_one is not None
        run_one.status = "success"
        run_one.current_phase = "completed"
        run_one.videos_found = 4
        run_one.videos_enqueued = 4
        run_one.videos_extracted = 4
        run_one.pending_video_count = 0
        run_one.last_event_at = datetime(2024, 1, 1, 1, 12, 0)
        run_one.updated_at = datetime(2024, 1, 1, 1, 12, 0)
        run_one.finished_at = datetime(2024, 1, 1, 1, 12, 0)

        session.add(
            SubscriptionSyncRunProjection(
                run_id="run-4",
                subscription_id=2,
                sync_state_id=2,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-4",
                trace_id="trace-4",
                status="running",
                current_phase="extracting",
                queued_at=datetime(2024, 1, 1, 1, 5, 0),
                started_at=datetime(2024, 1, 1, 1, 5, 5),
                finished_at=None,
                duration_ms=0,
                failure_count=0,
                error_type=None,
                error_message=None,
                videos_found=5,
                videos_enqueued=5,
                videos_extracted=2,
                videos_skipped=0,
                pending_video_count=3,
                last_event_seq_no=4,
                last_event_at=datetime(2024, 1, 1, 1, 10, 0),
                created_at=datetime(2024, 1, 1, 1, 5, 0),
                updated_at=datetime(2024, 1, 1, 1, 10, 0),
            ),
        )
        session.add(
            SubscriptionSyncSubscriptionProjection(
                subscription_id=2,
                latest_run_id="run-4",
                current_status="running",
                current_phase="extracting",
                last_sync_at=datetime(2024, 1, 1, 1, 5, 5),
                last_success_at=None,
                next_sync_at=datetime(2024, 1, 1, 2, 5, 0),
                last_error_message=None,
                pending_video_count=3,
                failure_streak=0,
                last_event_seq_no=4,
                updated_at=datetime(2024, 1, 1, 1, 10, 0),
            ),
        )
        session.add_all([
            SubscriptionSyncEvent(
                stream_id="run-1",
                subscription_id=1,
                sync_state_id=1,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-1",
                trace_id="trace-1",
                event_type="phase_changed",
                event_phase="extracting",
                event_status="running",
                seq_no=1,
                payload={},
                occurred_at=datetime(2024, 1, 1, 1, 2, 0),
                projected_at=datetime(2024, 1, 1, 1, 2, 0),
                created_at=datetime(2024, 1, 1, 1, 2, 0),
            ),
            SubscriptionSyncEvent(
                stream_id="run-1",
                subscription_id=1,
                sync_state_id=1,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-1",
                trace_id="trace-1",
                event_type="completed",
                event_phase="completed",
                event_status="success",
                seq_no=2,
                payload={},
                occurred_at=datetime(2024, 1, 1, 1, 12, 0),
                projected_at=datetime(2024, 1, 1, 1, 12, 0),
                created_at=datetime(2024, 1, 1, 1, 12, 0),
            ),
            SubscriptionSyncEvent(
                stream_id="run-4",
                subscription_id=2,
                sync_state_id=2,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-4",
                trace_id="trace-4",
                event_type="phase_changed",
                event_phase="extracting",
                event_status="running",
                seq_no=1,
                payload={},
                occurred_at=datetime(2024, 1, 1, 1, 5, 0),
                projected_at=datetime(2024, 1, 1, 1, 5, 0),
                created_at=datetime(2024, 1, 1, 1, 5, 0),
            ),
            SubscriptionSyncEvent(
                stream_id="run-4",
                subscription_id=2,
                sync_state_id=2,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-4",
                trace_id="trace-4",
                event_type="video_extracted",
                event_phase="extracting",
                event_status="running",
                seq_no=2,
                payload={},
                occurred_at=datetime(2024, 1, 1, 1, 10, 0),
                projected_at=datetime(2024, 1, 1, 1, 10, 0),
                created_at=datetime(2024, 1, 1, 1, 10, 0),
            ),
        ])
        session.commit()

    result = history_svc.list_runs(user_id=1, status="feed_recent", page=1, page_size=20)

    assert [item["run_id"] for item in result["data"]] == ["run-4", "run-1"]
    assert result["data"][0]["feed_completed_at"] == "2024-01-01 01:05:00"
    assert result["data"][1]["feed_completed_at"] == "2024-01-01 01:02:00"


def test_list_runs_feed_recent_only_returns_latest_run_per_subscription(engine, session_factory, monkeypatch):
    engine = _setup_test_env(engine, monkeypatch)
    _seed_sync_projection(engine)
    history_svc = SubscriptionSyncHistoryService(session_factory=session_factory)

    with Session(engine, expire_on_commit=False) as session:
        subscription_projection = session.get(SubscriptionSyncSubscriptionProjection, 1)
        assert subscription_projection is not None
        subscription_projection.latest_run_id = "run-4"
        subscription_projection.current_status = "running"
        subscription_projection.current_phase = "extracting"
        subscription_projection.updated_at = datetime(2024, 1, 1, 1, 5, 6)

        session.add(
            SubscriptionSyncRunProjection(
                run_id="run-4",
                subscription_id=1,
                sync_state_id=1,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-4",
                trace_id="trace-4",
                status="running",
                current_phase="extracting",
                queued_at=datetime(2024, 1, 1, 1, 5, 0),
                started_at=datetime(2024, 1, 1, 1, 5, 5),
                finished_at=None,
                duration_ms=0,
                failure_count=0,
                error_type=None,
                error_message=None,
                videos_found=4,
                videos_enqueued=4,
                videos_extracted=1,
                videos_skipped=0,
                pending_video_count=3,
                last_event_seq_no=3,
                last_event_at=datetime(2024, 1, 1, 1, 5, 6),
                created_at=datetime(2024, 1, 1, 1, 5, 0),
                updated_at=datetime(2024, 1, 1, 1, 5, 6),
            ),
        )
        session.add_all([
            SubscriptionSyncEvent(
                stream_id="run-1",
                subscription_id=1,
                sync_state_id=1,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-1",
                trace_id="trace-1",
                event_type="completed",
                event_phase="completed",
                event_status="success",
                seq_no=1,
                payload={},
                occurred_at=datetime(2024, 1, 1, 1, 2, 0),
                projected_at=datetime(2024, 1, 1, 1, 2, 0),
                created_at=datetime(2024, 1, 1, 1, 2, 0),
            ),
            SubscriptionSyncEvent(
                stream_id="run-4",
                subscription_id=1,
                sync_state_id=1,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-4",
                trace_id="trace-4",
                event_type="phase_changed",
                event_phase="extracting",
                event_status="running",
                seq_no=1,
                payload={},
                occurred_at=datetime(2024, 1, 1, 1, 5, 6),
                projected_at=datetime(2024, 1, 1, 1, 5, 6),
                created_at=datetime(2024, 1, 1, 1, 5, 6),
            ),
        ])
        session.commit()

    result = history_svc.list_runs(user_id=1, status="feed_recent", page=1, page_size=20)

    assert result["total"] == 1
    assert [item["run_id"] for item in result["data"]] == ["run-4"]


def test_list_sync_center_queued_items_follow_real_task_queue_order(engine, session_factory, monkeypatch):
    engine = _setup_test_env(engine, monkeypatch)
    _seed_sync_projection(engine)
    svc = SubscriptionSyncCenterService(session_factory=session_factory)

    with Session(engine, expire_on_commit=False) as session:
        subscription_projection = session.get(SubscriptionSyncSubscriptionProjection, 1)
        assert subscription_projection is not None
        subscription_projection.latest_run_id = "run-queued-a"
        subscription_projection.current_status = "queued"
        subscription_projection.current_phase = "queued"
        subscription_projection.last_sync_at = datetime(2024, 1, 1, 1, 0, 0)
        subscription_projection.last_success_at = datetime(2024, 1, 1, 1, 0, 0)
        subscription_projection.next_sync_at = datetime(2024, 1, 1, 2, 0, 0)
        subscription_projection.last_event_seq_no = 1
        subscription_projection.updated_at = datetime(2024, 1, 1, 1, 0, 0)

        session.add(
            Subscription(
                id=2,
                type="CHANNEL",
                name="Second Channel",
                url="https://www.youtube.com/channel/demo-2",
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
        )
        session.add(
            UserSubscription(
                id=2,
                user_id=1,
                subscription_id=2,
                is_deleted=False,
                is_nsfw=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
        )
        session.add_all([
            SubscriptionSyncRunProjection(
                run_id="run-queued-a",
                subscription_id=1,
                sync_state_id=11,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-queued-a",
                trace_id="trace-queued-a",
                status="queued",
                current_phase="queued",
                queued_at=datetime(2024, 1, 1, 1, 0, 0),
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
                last_event_seq_no=1,
                last_event_at=datetime(2024, 1, 1, 1, 0, 0),
                created_at=datetime(2024, 1, 1, 1, 0, 0),
                updated_at=datetime(2024, 1, 1, 1, 0, 0),
            ),
            SubscriptionSyncRunProjection(
                run_id="run-queued-b",
                subscription_id=2,
                sync_state_id=12,
                site="youtube.com",
                sync_mode="incremental",
                trigger="manual",
                request_id="req-queued-b",
                trace_id="trace-queued-b",
                status="queued",
                current_phase="queued",
                queued_at=datetime(2024, 1, 1, 0, 0, 0),
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
                last_event_seq_no=1,
                last_event_at=datetime(2024, 1, 1, 0, 0, 0),
                created_at=datetime(2024, 1, 1, 0, 0, 0),
                updated_at=datetime(2024, 1, 1, 0, 0, 0),
            ),
            SubscriptionSyncSubscriptionProjection(
                subscription_id=2,
                latest_run_id="run-queued-b",
                current_status="queued",
                current_phase="queued",
                last_sync_at=datetime(2024, 1, 1, 0, 0, 0),
                last_success_at=datetime(2024, 1, 1, 0, 0, 0),
                next_sync_at=datetime(2024, 1, 1, 2, 0, 0),
                last_error_message=None,
                pending_video_count=0,
                failure_streak=0,
                last_event_seq_no=1,
                updated_at=datetime(2024, 1, 1, 0, 0, 0),
            ),
            CrawlTask(
                id=101,
                job_id=1,
                task_type="subscription_sync",
                site="youtube.com",
                subscription_id=1,
                status="pending",
                priority="normal",
                payload={"sync_state_id": 11},
                next_run_at=datetime(2024, 1, 1, 0, 0, 0),
                created_at=datetime(2024, 1, 1, 0, 0, 0),
                updated_at=datetime(2024, 1, 1, 0, 0, 0),
            ),
            CrawlTask(
                id=102,
                job_id=1,
                task_type="subscription_sync",
                site="youtube.com",
                subscription_id=2,
                status="pending",
                priority="normal",
                payload={"sync_state_id": 12},
                next_run_at=datetime(2024, 1, 1, 1, 0, 0),
                created_at=datetime(2024, 1, 1, 1, 0, 0),
                updated_at=datetime(2024, 1, 1, 1, 0, 0),
            ),
        ])
        session.commit()

    result = svc.list_queued_items(user_id=1, page=1, page_size=20)

    assert result["total"] == 2
    assert [item["subscription_id"] for item in result["data"]] == [2, 1]
