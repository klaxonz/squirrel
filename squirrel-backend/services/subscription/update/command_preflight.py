from __future__ import annotations

from collections.abc import Callable

from services.site_catalog.catalog import SiteCatalog
from services.subscription.update.command_events import SubscriptionSyncCommandEventPublisher
from services.subscription.update.models import (
    SubscriptionDirectRunResult,
    SubscriptionScheduleResult,
    SubscriptionUpdateResult,
    SyncCommand,
)


def resolve_preflight_result(
    command: SyncCommand,
    domain: str | None,
    *,
    direct: bool,
    event_publisher: SubscriptionSyncCommandEventPublisher,
    has_active_subscribers: Callable[[int], bool],
) -> SubscriptionScheduleResult | SubscriptionDirectRunResult | None:
    if not domain or not SiteCatalog.is_site_enabled(domain=domain):
        return _deferred_result(
            command,
            domain,
            reason='site_disabled',
            direct=direct,
            event_publisher=event_publisher,
        )

    if not has_active_subscribers(command.subscription_id):
        return _deferred_result(
            command,
            domain,
            reason='no_subscribers',
            direct=direct,
            event_publisher=event_publisher,
        )
    return None


def _deferred_result(
    command: SyncCommand,
    domain: str | None,
    *,
    reason: str,
    direct: bool,
    event_publisher: SubscriptionSyncCommandEventPublisher,
) -> SubscriptionScheduleResult | SubscriptionDirectRunResult:
    run_context = event_publisher.emit_deferred_event(command, None, domain, reason)
    if direct:
        return SubscriptionDirectRunResult(
            command.subscription_id,
            None,
            reason,
            run_id=run_context.run_id,
            result=SubscriptionUpdateResult(
                subscription_id=command.subscription_id,
                success=True,
                videos_found=0,
                videos_enqueued=0,
                skipped_reason=reason,
            ),
        )
    return SubscriptionScheduleResult(command.subscription_id, None, reason, run_id=run_context.run_id)
