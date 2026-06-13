from datetime import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from models import Base
from models.links import UserSubscription
from models.subscription import Subscription
from models.subscription_sync_event import SubscriptionSyncEvent
from models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from services.subscription.sync.history_service import SubscriptionSyncHistoryService


@pytest.fixture
def engine(engine):
    Base.metadata.create_all(
        engine,
        tables=[
            Subscription.__table__,
            UserSubscription.__table__,
            SubscriptionSyncRunProjection.__table__,
            SubscriptionSyncEvent.__table__,
        ],
    )
    return engine


def _seed_runs_and_subscription(engine):
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            Subscription(
                id=1,
                type="CHANNEL",
                name="Demo",
                url="https://youtube.com/channel/demo",
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
                queued_at=datetime(2024, 1, 1, 12, 0, 0),
                started_at=datetime(2024, 1, 1, 12, 1, 0),
                finished_at=datetime(2024, 1, 1, 12, 2, 0),
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
                last_event_at=datetime(2024, 1, 1, 12, 2, 0),
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                updated_at=datetime(2024, 1, 1, 12, 2, 0),
            ),
        )
        session.add(
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
                seq_no=3,
                message="done",
                payload={"videos_extracted": 2},
                occurred_at=datetime(2024, 1, 1, 12, 2, 0),
                created_at=datetime(2024, 1, 1, 12, 2, 0),
            ),
        )
        session.commit()


def test_list_runs_uses_count_helper_instead_of_loading_all_rows(engine, session_factory, monkeypatch):
    _seed_runs_and_subscription(engine)

    svc = SubscriptionSyncHistoryService(
        session_factory=session_factory,
        site_icon_resolver=SimpleNamespace(resolve=lambda site: None),
    )

    count_queries = []

    def fake_count_query_rows(current_session, query):
        count_queries.append((current_session, query))
        return 1

    monkeypatch.setattr(
        "services.subscription.sync.history_service.count_query_rows",
        fake_count_query_rows,
    )
    result = svc.list_runs(user_id=1, page=1, page_size=20)

    assert result["total"] == 1
    assert len(result["data"]) == 1
    assert len(count_queries) == 1


def test_list_run_events_checks_access_without_calling_get_run_detail(engine, session_factory, monkeypatch):
    _seed_runs_and_subscription(engine)

    svc = SubscriptionSyncHistoryService(session_factory=session_factory)

    monkeypatch.setattr(
        "services.subscription.sync.history_service.run_exists_for_user",
        lambda current_session, run_id, user_id: True,
    )

    result = svc.list_run_events("run-1", 1)

    assert len(result) == 1
    assert result[0]["stream_id"] == "run-1"
