from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from domains.subscription.application.services.core.sync.run_service import subscription_sync_run_service
from domains.subscription.domain.models.subscription_sync_event import SubscriptionSyncEvent
from infrastructure.database.session import get_session


@dataclass
class SyncEventInput:
    stream_id: str
    subscription_id: int
    sync_mode: str
    event_type: str
    sync_state_id: int | None = None
    site: str | None = None
    trigger: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    event_phase: str | None = None
    event_status: str | None = None
    payload: dict | None = None
    message: str | None = None
    occurred_at: datetime | None = None
    seq_no: int | None = None


class SubscriptionSyncEventService:
    """Append-only writer for the subscription sync event stream.

    The sync dashboard / SSE invalidation hooks and the run/subscription/trend projection writers
    have been removed. This service now only persists events to ``subscription_sync_event``;
    ``next_seq_no`` still reads that table to allocate sequence numbers. The ``project`` parameter
    is accepted for backwards compatibility but is a no-op.
    """

    def __init__(self, session_factory=get_session, run_service=None):
        self.session_factory = session_factory
        self.run_service = run_service or subscription_sync_run_service

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {str(key): SubscriptionSyncEventService._serialize_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [SubscriptionSyncEventService._serialize_value(item) for item in value]
        return value

    @staticmethod
    def serialize_payload(payload: dict | None) -> dict:
        if not payload:
            return {}
        return SubscriptionSyncEventService._serialize_value(dict(payload))

    def build_event(self, event_input: SyncEventInput, *, session: Session | None = None) -> SubscriptionSyncEvent:
        event_time = event_input.occurred_at or datetime.now()
        seq_no = event_input.seq_no
        if seq_no is None:
            seq_no = self.run_service.next_seq_no(event_input.stream_id, session=session)

        return SubscriptionSyncEvent(
            stream_id=event_input.stream_id,
            subscription_id=event_input.subscription_id,
            sync_state_id=event_input.sync_state_id,
            site=(event_input.site or '').strip() or None,
            sync_mode=event_input.sync_mode,
            trigger=event_input.trigger,
            request_id=event_input.request_id,
            trace_id=event_input.trace_id,
            event_type=event_input.event_type,
            event_phase=event_input.event_phase,
            event_status=event_input.event_status,
            seq_no=seq_no,
            payload=self.serialize_payload(event_input.payload),
            message=event_input.message,
            occurred_at=event_time,
            created_at=event_time,
        )

    def append_event(self, event_input: SyncEventInput, *, session: Session | None = None, project: bool = True) -> SubscriptionSyncEvent:
        if session is not None:
            event = self.build_event(event_input, session=session)
            session.add(event)
            session.flush()
            return event

        with self.session_factory() as managed_session:
            return self.append_event(event_input, session=managed_session, project=project)

    def append_events(self, event_inputs: list[SyncEventInput], *, session: Session | None = None, project: bool = True) -> list[SubscriptionSyncEvent]:
        if session is not None:
            ordered_inputs = sorted(
                event_inputs,
                key=lambda event_input: (
                    event_input.occurred_at or datetime.max,
                    event_input.stream_id,
                    event_input.event_type,
                ),
            )
            events: list[SubscriptionSyncEvent] = []
            for event_input in ordered_inputs:
                events.append(self.build_event(event_input, session=session))

            ordered_events = sorted(
                events,
                key=lambda event: (event.occurred_at, event.stream_id, event.seq_no, event.event_type),
            )
            for event in ordered_events:
                session.add(event)
            session.flush()
            return events

        with self.session_factory() as managed_session:
            return self.append_events(event_inputs, session=managed_session, project=project)


subscription_sync_event_service = SubscriptionSyncEventService()
serialize_payload = subscription_sync_event_service.serialize_payload
build_event = subscription_sync_event_service.build_event
append_event = subscription_sync_event_service.append_event
append_events = subscription_sync_event_service.append_events
