from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from infrastructure.database.session import get_session
from domains.subscription.domain.models.subscription_sync_event import SubscriptionSyncEvent
from domains.subscription.application.services.core.sync.projection.run import apply_run_projection
from domains.subscription.application.services.core.sync.projection.store import (
    get_or_create_run_projection,
    get_or_create_subscription_projection,
)
from domains.subscription.application.services.core.sync.projection.subscription import apply_subscription_projection
from domains.subscription.application.services.core.sync.projection.trend import apply_trend_projection


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
