from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from core.database import get_session
from models.subscription_sync_event import SubscriptionSyncEvent
from services.subscription.sync.projection.run import apply_run_projection
from services.subscription.sync.projection.store import (
    get_or_create_run_projection,
    get_or_create_subscription_projection,
)
from services.subscription.sync.projection.subscription import apply_subscription_projection
from services.subscription.sync.projection.trend import apply_trend_projection


class SubscriptionSyncProjectionService:
    def __init__(self, session_factory=get_session):
        self.session_factory = session_factory

    def apply_event(self, event: SubscriptionSyncEvent, *, session: Session | None = None) -> SubscriptionSyncEvent:
        if session is not None:
            if event.projected_at:
                return event
            run_projection = get_or_create_run_projection(session, event)
            apply_run_projection(run_projection, event)

            subscription_projection = get_or_create_subscription_projection(session, event)
            apply_subscription_projection(subscription_projection, event)
            apply_trend_projection(session, event)
            event.projected_at = datetime.now()
            return event

        with self.session_factory() as managed_session:
            return self.apply_event(event, session=managed_session)

    def apply_events(self, events: list[SubscriptionSyncEvent], *, session: Session | None = None) -> list[SubscriptionSyncEvent]:
        if session is not None:
            ordered_events = sorted(events, key=lambda event: (event.occurred_at, event.stream_id, event.seq_no, event.id or 0))
            for event in ordered_events:
                self.apply_event(event, session=session)
            return events

        with self.session_factory() as managed_session:
            return self.apply_events(events, session=managed_session)


subscription_sync_projection_service = SubscriptionSyncProjectionService()
apply_event = subscription_sync_projection_service.apply_event
apply_events = subscription_sync_projection_service.apply_events
