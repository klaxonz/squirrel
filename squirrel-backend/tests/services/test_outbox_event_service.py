from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from models import Base
from models.crawl_dispatch_scope import CrawlDispatchScope
from models.crawl_job import CrawlJob
from models.crawl_task import CrawlTask
from models.outbox_event import OutboxEvent
from models.subscription_sync_state import SubscriptionSyncState
from services.outbox.event_service import OutboxEventService


@pytest.fixture
def engine(engine):
    Base.metadata.create_all(
        engine,
        tables=[
            OutboxEvent.__table__,
            CrawlJob.__table__,
            CrawlTask.__table__,
            CrawlDispatchScope.__table__,
            SubscriptionSyncState.__table__,
        ],
    )
    return engine


@pytest.fixture
def svc(session_factory):
    return OutboxEventService(session_factory=session_factory)


def test_publish_event_persists_pending_outbox_row(engine, svc):
    event = svc.publish_event(
        event_type="full_backfill_requested",
        event_key="full_backfill_requested:11:2026-04-04T10:00",
        aggregate_type="subscription",
        aggregate_id="11",
        payload={"subscription_id": 1, "sync_state_id": 11, "mode": "full"},
    )

    assert event.status == "pending"
    assert event.attempt_count == 0
    assert event.available_at is not None

    with Session(engine, expire_on_commit=False) as session:
        stored = session.get(OutboxEvent, event.id)

    assert stored is not None
    assert stored.event_type == "full_backfill_requested"
    assert stored.payload["sync_state_id"] == 11


def test_consume_sync_due_event_is_unsupported_and_does_not_create_task(engine, svc):
    now = datetime(2026, 4, 4, 12, 0, 0)

    svc.publish_event(
        event_type="incremental_sync_due",
        event_key="incremental_sync_due:11:2026-04-04T12:00",
        aggregate_type="subscription_sync_state",
        aggregate_id="11",
        payload={
            "subscription_id": 1,
            "sync_state_id": 11,
            "url": "https://space.bilibili.com/1",
            "mode": "incremental",
            "trigger": "scheduled",
        },
        available_at=now - timedelta(seconds=1),
    )

    summary = svc.consume_available_events(limit=10, now=now)

    assert summary == {"processed": 1, "failed": 0}

    with Session(engine, expire_on_commit=False) as session:
        tasks = session.query(CrawlTask).all()
        events = session.query(OutboxEvent).all()

    assert tasks == []
    assert events[0].status == "done"


def test_full_backfill_request_dispatches_full_sync_command(engine, session_factory, svc):
    now = datetime(2026, 4, 4, 12, 0, 0)
    request_calls = []

    from core import database
    from core.config import settings
    from services.subscription.update.commands import SubscriptionSyncCommandService
    from services.subscription.update.models import UpdateMode, UpdateTrigger

    with patch.object(database, 'get_session', session_factory), \
         patch.object(settings, 'FULL_SYNC_MAX_INFLIGHT', 10), \
         patch.object(settings, 'FULL_SYNC_SITE_MAX_INFLIGHT', 10), \
         patch("services.outbox.event_service.get_subscription_by_id", return_value=None), \
         patch.object(
             SubscriptionSyncCommandService,
             "request_sync",
             lambda self, **kwargs: request_calls.append(kwargs),
         ):
        svc.publish_event(
            event_type="full_backfill_requested",
            event_key="full_backfill_requested:7:gap:20260404",
            aggregate_type="subscription",
            aggregate_id="7",
            payload={
                "subscription_id": 7,
                "sync_state_id": 21,
                "url": "https://www.youtube.com/channel/demo",
                "site": "youtube.com",
                "trigger": "scheduled",
                "trace_id": "trace-1",
            },
            available_at=now - timedelta(seconds=1),
        )

        summary = svc.consume_available_events(limit=10, now=now)

    assert summary == {"processed": 1, "failed": 0}
    assert request_calls == [{
        "subscription_id": 7,
        "url": "https://www.youtube.com/channel/demo",
        "trigger": UpdateTrigger.SCHEDULED,
        "mode": UpdateMode.FULL,
        "trace_id": "trace-1",
    }]


def test_full_backfill_request_is_deferred_when_full_budget_is_exhausted(engine, session_factory, svc):
    now = datetime(2026, 4, 4, 12, 0, 0)

    from core import database
    from core.config import settings

    with patch.object(settings, 'FULL_SYNC_MAX_INFLIGHT', 1), \
         patch.object(settings, 'FULL_SYNC_SITE_MAX_INFLIGHT', 1), \
         patch.object(settings, 'FULL_BACKFILL_RETRY_SECONDS', 300), \
         patch.object(database, 'get_session', session_factory):

        with Session(engine, expire_on_commit=False) as session:
            session.add(
                SubscriptionSyncState(
                    id=30,
                    subscription_id=3,
                    site="youtube.com",
                    sync_mode="full",
                    sync_status="running",
                    next_sync_at=now,
                ),
            )
            session.commit()

        svc.publish_event(
            event_type="full_backfill_requested",
            event_key="full_backfill_requested:7:gap:20260404",
            aggregate_type="subscription",
            aggregate_id="7",
            payload={
                "subscription_id": 7,
                "sync_state_id": 21,
                "site": "youtube.com",
                "trigger": "scheduled",
            },
            available_at=now - timedelta(seconds=1),
        )

        summary = svc.consume_available_events(limit=10, now=now)

    assert summary == {"processed": 0, "failed": 0}

    with Session(engine, expire_on_commit=False) as session:
        events = session.query(OutboxEvent).order_by(OutboxEvent.id.asc()).all()

    assert len(events) == 1
    assert events[0].event_type == "full_backfill_requested"
    assert events[0].status == "pending"
    assert events[0].available_at == now + timedelta(seconds=300)
