import sys
from contextlib import contextmanager
from datetime import datetime, timedelta
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models import Base
from models.crawl_dispatch_scope import CrawlDispatchScope
from models.crawl_job import CrawlJob
from models.crawl_task import CrawlTask
from models.outbox_event import OutboxEvent
from models.subscription_sync_state import SubscriptionSyncState
from services import outbox_event_service, subscription_sync_state_service
from services.crawl_tasks import service as crawl_task_service
from services.subscription_update.scheduler import SubscriptionScheduler

scheduler_module = import_module("services.subscription_update.scheduler")


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
    engine = create_engine("sqlite:///:memory:")
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
    monkeypatch.setattr(outbox_event_service, "get_session", lambda: _managed_session(engine))
    monkeypatch.setattr(crawl_task_service, "get_session", lambda: _managed_session(engine))
    monkeypatch.setattr(subscription_sync_state_service, "get_session", lambda: _managed_session(engine))
    from core import database
    monkeypatch.setattr(database, "get_session", lambda: _managed_session(engine))
    return engine


def test_publish_event_persists_pending_outbox_row(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    event = outbox_event_service.publish_event(
        event_type="incremental_sync_due",
        event_key="incremental_sync_due:11:2026-04-04T10:00",
        aggregate_type="subscription_sync_state",
        aggregate_id="11",
        payload={"subscription_id": 1, "sync_state_id": 11, "mode": "incremental"},
    )

    assert event.status == "pending"
    assert event.attempt_count == 0
    assert event.available_at is not None

    with Session(engine, expire_on_commit=False) as session:
        stored = session.get(OutboxEvent, event.id)

    assert stored is not None
    assert stored.event_type == "incremental_sync_due"
    assert stored.payload["sync_state_id"] == 11


def test_consume_due_event_creates_subscription_sync_task(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    now = datetime(2026, 4, 4, 12, 0, 0)
    monkeypatch.setattr(scheduler_module.SiteCatalog, "is_site_enabled", lambda domain=None, site=None: True)
    monkeypatch.setattr(SubscriptionScheduler, "_has_active_subscribers", staticmethod(lambda subscription_id: True))
    monkeypatch.setattr(
        scheduler_module,
        "create_run",
        lambda **kwargs: SimpleNamespace(run_id="run-1", created_at=now),
    )
    monkeypatch.setattr(scheduler_module, "append_event", lambda *args, **kwargs: None)

    with Session(engine, expire_on_commit=False) as session:
        state = SubscriptionSyncState(
            id=11,
            subscription_id=1,
            site="bilibili.com",
            sync_mode="incremental",
            sync_status="idle",
            next_sync_at=now - timedelta(minutes=1),
        )
        session.add(state)
        session.commit()

    outbox_event_service.publish_event(
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

    summary = outbox_event_service.consume_available_events(limit=10, now=now)

    assert summary == {"processed": 1, "failed": 0}

    with Session(engine, expire_on_commit=False) as session:
        tasks = session.query(CrawlTask).all()
        events = session.query(OutboxEvent).all()

    assert len(tasks) == 1
    assert tasks[0].task_type == "subscription_sync_incremental"
    assert tasks[0].payload["mode"] == "incremental"
    assert events[0].status == "done"


def test_full_backfill_request_is_deferred_when_full_budget_is_exhausted(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    now = datetime(2026, 4, 4, 12, 0, 0)
    monkeypatch.setattr(outbox_event_service.settings, "FULL_SYNC_MAX_INFLIGHT", 1, raising=False)
    monkeypatch.setattr(outbox_event_service.settings, "FULL_SYNC_SITE_MAX_INFLIGHT", 1, raising=False)
    monkeypatch.setattr(outbox_event_service.settings, "FULL_BACKFILL_RETRY_SECONDS", 300, raising=False)

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

    outbox_event_service.publish_event(
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

    summary = outbox_event_service.consume_available_events(limit=10, now=now)

    assert summary == {"processed": 0, "failed": 0}

    with Session(engine, expire_on_commit=False) as session:
        events = session.query(OutboxEvent).order_by(OutboxEvent.id.asc()).all()

    assert len(events) == 1
    assert events[0].event_type == "full_backfill_requested"
    assert events[0].status == "pending"
    assert events[0].available_at == now + timedelta(seconds=300)
