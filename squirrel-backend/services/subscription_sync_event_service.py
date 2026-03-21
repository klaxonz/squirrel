from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.database import get_session
from models.subscription_sync_event import SubscriptionSyncEvent
from services import subscription_sync_projection_service, subscription_sync_run_service


@dataclass
class SyncEventInput:
    stream_id: str
    subscription_id: int
    sync_mode: str
    event_type: str
    sync_state_id: Optional[int] = None
    site: Optional[str] = None
    trigger: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    event_phase: Optional[str] = None
    event_status: Optional[str] = None
    payload: Optional[dict] = None
    message: Optional[str] = None
    occurred_at: Optional[datetime] = None
    seq_no: Optional[int] = None


def serialize_payload(payload: Optional[dict]) -> dict:
    if not payload:
        return {}
    return dict(payload)


def build_event(event_input: SyncEventInput, *, session=None) -> SubscriptionSyncEvent:
    event_time = event_input.occurred_at or datetime.now()
    seq_no = event_input.seq_no
    if seq_no is None:
        seq_no = subscription_sync_run_service.next_seq_no(event_input.stream_id, session=session)

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
        payload=serialize_payload(event_input.payload),
        message=event_input.message,
        occurred_at=event_time,
        created_at=event_time,
    )


def append_event(event_input: SyncEventInput, *, session=None, project: bool = True) -> SubscriptionSyncEvent:
    if session is not None:
        event = build_event(event_input, session=session)
        session.add(event)
        session.flush()
        if project:
            subscription_sync_projection_service.apply_event(event, session=session)
        return event

    with get_session() as managed_session:
        return append_event(event_input, session=managed_session, project=project)


def append_events(event_inputs: list[SyncEventInput], *, session=None, project: bool = True) -> list[SubscriptionSyncEvent]:
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
            events.append(build_event(event_input, session=session))

        ordered_events = sorted(
            events,
            key=lambda event: (event.occurred_at, event.stream_id, event.seq_no, event.event_type),
        )
        for event in ordered_events:
            session.add(event)
        session.flush()

        if project:
            subscription_sync_projection_service.apply_events(ordered_events, session=session)
        return events

    with get_session() as managed_session:
        return append_events(event_inputs, session=managed_session, project=project)
