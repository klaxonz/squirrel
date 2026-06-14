from __future__ import annotations

import logging
import select as io_select
from collections.abc import Callable, Generator
from datetime import datetime, timedelta
from threading import Event

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domains.subscription.application.services.core.crud import get_subscription_by_id
from domains.subscription.domain.models.outbox_event import OutboxEvent
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState, SyncMode
from infrastructure.config.settings import settings
from infrastructure.database.session import engine
from infrastructure.database.session import get_session as _default_get_session

SessionFactory = Callable[[], Generator[Session, None, None]]

logger = logging.getLogger(__name__)


class RetryLaterError(Exception):
    def __init__(self, delay_seconds: int) -> None:
        super().__init__(f"retry later in {delay_seconds} seconds")
        self.delay_seconds = delay_seconds


class OutboxEventService:
    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session

    def publish_event(
        self,
        *,
        event_type: str,
        event_key: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict | None = None,
        priority: str = "normal",
        available_at: datetime | None = None,
        max_attempts: int = 3,
    ) -> OutboxEvent:
        with self._session_factory() as session:
            event = OutboxEvent(
                event_type=event_type,
                event_key=event_key,
                aggregate_type=aggregate_type,
                aggregate_id=str(aggregate_id),
                payload=payload or {},
                priority=priority,
                available_at=available_at or datetime.now(),
                max_attempts=max_attempts,
            )
            session.add(event)
            try:
                session.flush()
                self._notify_new_event(session, event_type=event_type)
                return event
            except IntegrityError:
                session.rollback()
                existing = session.execute(
                    select(OutboxEvent).where(OutboxEvent.event_key == event_key),
                ).scalar_one()
                return existing

    def publish_event_in_session(
        self,
        session: Session,
        *,
        event_type: str,
        event_key: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict | None = None,
        priority: str = "normal",
        available_at: datetime | None = None,
        max_attempts: int = 3,
    ) -> OutboxEvent:
        event = OutboxEvent(
            event_type=event_type,
            event_key=event_key,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            payload=payload or {},
            priority=priority,
            available_at=available_at or datetime.now(),
            max_attempts=max_attempts,
        )
        session.add(event)
        try:
            session.flush()
            self._notify_new_event(session, event_type=event_type)
            return event
        except IntegrityError:
            session.rollback()
            return session.execute(
                select(OutboxEvent).where(OutboxEvent.event_key == event_key),
            ).scalar_one()

    def consume_available_events(self, *, limit: int = 50, now: datetime | None = None, worker_id: str = "scheduler") -> dict[str, int]:
        now = now or datetime.now()
        processed = 0
        failed = 0

        with self._session_factory() as session:
            events = session.execute(
                select(OutboxEvent)
                .where(
                    OutboxEvent.status == "pending",
                    OutboxEvent.available_at <= now,
                )
                .order_by(OutboxEvent.available_at.asc(), OutboxEvent.id.asc())
                .limit(limit),
            ).scalars().all()

            event_ids = [event.id for event in events]
            for event in events:
                event.status = "processing"
                event.locked_by = worker_id
                event.locked_at = now
            session.flush()

        for event_id in event_ids:
            try:
                self._handle_claimed_event(event_id=event_id, worker_id=worker_id, now=now)
                processed += 1
            except RetryLaterError as exc:
                self._reschedule_event(event_id=event_id, delay_seconds=exc.delay_seconds, now=now)
            except Exception as exc:  # event consumer boundary — catch all to mark failed
                failed += 1
                logger.exception("Failed to consume outbox event id=%s", event_id)
                self._mark_event_failed(event_id=event_id, error_message=str(exc), now=now)

        return {"processed": processed, "failed": failed}

    def _handle_claimed_event(self, *, event_id: int, worker_id: str, now: datetime) -> None:
        with self._session_factory() as session:
            event = session.get(OutboxEvent, event_id)
            if not event or event.status != "processing" or event.locked_by != worker_id:
                return

            self._handle_event(event)
            event.status = "done"
            event.processed_at = now
            event.last_error = None
            event.locked_by = None
            event.locked_at = None
            session.flush()

    def _handle_event(self, event: OutboxEvent) -> None:
        if event.event_type == "full_backfill_requested":
            self._handle_full_backfill_requested(event)
            return
        logger.info("Skip unsupported outbox event type=%s id=%s", event.event_type, event.id)

    def _handle_full_backfill_requested(self, event: OutboxEvent) -> None:
        import domains.subscription.application.services.core.sync.state.service as subscription_sync_state_service
        from domains.subscription.application.services.core.update.commands import SubscriptionSyncCommandService
        from domains.subscription.application.services.core.update.models import UpdateMode

        payload = event.payload or {}
        subscription_id = int(payload["subscription_id"])
        full_state = subscription_sync_state_service.get_sync_state(subscription_id, UpdateMode.FULL.value)
        if full_state and full_state.sync_status in {"queued", "running"}:
            return

        site = str(payload.get("site") or getattr(full_state, "site", "") or "").strip()
        if not site and payload.get("sync_state_id"):
            source_state = subscription_sync_state_service.get_sync_state_by_id(int(payload["sync_state_id"]))
            site = str(getattr(source_state, "site", "") or "").strip()

        snapshot = self._count_full_sync_pressure(site=site)
        if snapshot["global_inflight"] >= max(1, int(settings.FULL_SYNC_MAX_INFLIGHT)):
            raise RetryLaterError(int(settings.FULL_BACKFILL_RETRY_SECONDS))
        if site and snapshot["site_inflight"] >= max(1, int(settings.FULL_SYNC_SITE_MAX_INFLIGHT)):
            raise RetryLaterError(int(settings.FULL_BACKFILL_RETRY_SECONDS))

        command_service = SubscriptionSyncCommandService(session_factory=self._session_factory)
        subscription = get_subscription_by_id(subscription_id)
        command_service.request_sync(
            subscription_id=subscription_id,
            url=payload.get("url") or (subscription.url if subscription and subscription.url else ""),
            trigger=self._parse_trigger(payload.get("trigger")),
            mode=UpdateMode.FULL,
            trace_id=payload.get("trace_id"),
        )

    @staticmethod
    def _parse_trigger(raw: str | None):
        from domains.subscription.application.services.core.update.models import UpdateTrigger

        if str(raw).lower() == UpdateTrigger.MANUAL.value:
            return UpdateTrigger.MANUAL
        if str(raw).lower() == UpdateTrigger.API.value:
            return UpdateTrigger.API
        return UpdateTrigger.SCHEDULED

    def _count_full_sync_pressure(self, *, site: str) -> dict[str, int]:
        with self._session_factory() as session:
            global_inflight = int(session.execute(
                select(func.count(SubscriptionSyncState.id)).where(
                    SubscriptionSyncState.sync_mode == SyncMode.FULL.value,
                    SubscriptionSyncState.sync_status.in_(["queued", "running"]),
                ),
            ).scalar_one() or 0)
            site_inflight = 0
            if site:
                site_inflight = int(session.execute(
                    select(func.count(SubscriptionSyncState.id)).where(
                        SubscriptionSyncState.sync_mode == SyncMode.FULL.value,
                        SubscriptionSyncState.sync_status.in_(["queued", "running"]),
                        SubscriptionSyncState.site == site,
                    ),
                ).scalar_one() or 0)
            event_rows = session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.event_type == "full_backfill_requested",
                    OutboxEvent.status.in_(["pending", "processing"]),
                ),
            ).scalars().all()

        for event in event_rows:
            payload = event.payload or {}
            global_inflight += 1
            if site and str(payload.get("site") or "").strip() == site:
                site_inflight += 1
        return {
            "global_inflight": global_inflight,
            "site_inflight": site_inflight,
        }

    def _mark_event_failed(self, *, event_id: int, error_message: str, now: datetime) -> None:
        with self._session_factory() as session:
            event = session.get(OutboxEvent, event_id)
            if not event:
                return
            event.attempt_count += 1
            event.last_error = error_message
            event.locked_by = None
            event.locked_at = None
            if event.attempt_count >= event.max_attempts:
                event.status = "dead"
                event.processed_at = now
            else:
                event.status = "pending"
                event.available_at = now + timedelta(seconds=min(30 * event.attempt_count, 300))
            session.flush()

    def _reschedule_event(self, *, event_id: int, delay_seconds: int, now: datetime) -> None:
        with self._session_factory() as session:
            event = session.get(OutboxEvent, event_id)
            if not event:
                return
            event.status = "pending"
            event.locked_by = None
            event.locked_at = None
            event.available_at = now + timedelta(seconds=max(1, delay_seconds))
            session.flush()

    @staticmethod
    def _notify_new_event(session: Session, *, event_type: str) -> None:
        bind = session.get_bind()
        if bind is None or bind.dialect.name != "postgresql":
            return
        session.execute(select(func.pg_notify(settings.OUTBOX_NOTIFY_CHANNEL, event_type)))

    @staticmethod
    def create_listener_stop_event() -> Event:
        return Event()

    def run_notification_listener(self, stop_event: Event) -> None:
        timeout = max(1, int(settings.OUTBOX_NOTIFY_POLL_TIMEOUT_SECONDS))
        batch_size = max(1, int(settings.OUTBOX_CONSUME_BATCH_SIZE))
        if engine.dialect.name != "postgresql":
            while not stop_event.is_set():
                stop_event.wait(timeout)
                if stop_event.is_set():
                    break
                self.consume_available_events(limit=batch_size, worker_id="scheduler-listener")
            return

        while not stop_event.is_set():
            raw_conn = None
            cursor = None
            try:
                raw_conn = engine.raw_connection()
                raw_conn.set_session(autocommit=True)
                cursor = raw_conn.cursor()
                cursor.execute(f"LISTEN {settings.OUTBOX_NOTIFY_CHANNEL};")
                while not stop_event.is_set():
                    ready, _, _ = io_select.select([raw_conn], [], [], timeout)
                    if ready:
                        raw_conn.poll()
                        while raw_conn.notifies:
                            raw_conn.notifies.pop(0)
                            self.consume_available_events(limit=batch_size, worker_id="scheduler-listener")
                        continue
                    self.consume_available_events(limit=batch_size, worker_id="scheduler-listener")
            except Exception:  # listener boundary — catch all to keep polling
                logger.exception("Outbox notification listener failed; retrying")
                stop_event.wait(1)
            finally:
                if cursor is not None:
                    cursor.close()
                if raw_conn is not None:
                    raw_conn.close()


outbox_event_service = OutboxEventService()
publish_event = outbox_event_service.publish_event
publish_event_in_session = outbox_event_service.publish_event_in_session
consume_available_events = outbox_event_service.consume_available_events
create_listener_stop_event = outbox_event_service.create_listener_stop_event
run_notification_listener = outbox_event_service.run_notification_listener
