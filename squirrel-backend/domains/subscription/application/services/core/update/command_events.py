from __future__ import annotations

from datetime import datetime

from domains.subscription.application.services.core.sync.run_service import SyncRunContext, create_run


class SubscriptionSyncCommandEventPublisher:
    """Builds ``SyncRunContext`` correlation IDs for the sync command path.

    The event-emission methods were removed together with the ``subscription_sync_event`` table;
    only ``build_run_context`` (which generates the in-memory run_id) is retained because run_id
    is persisted on CrawlTask payloads and surfaced in API responses.
    """

    @staticmethod
    def build_run_context(
        *,
        subscription_id: int,
        sync_state_id: int | None,
        site: str | None,
        sync_mode: str,
        trigger: str,
        trace_id: str,
        run_id: str | None,
    ) -> tuple[SyncRunContext, bool]:
        if run_id:
            now = datetime.now()
            return (
                SyncRunContext(
                    run_id=run_id,
                    stream_id=run_id,
                    subscription_id=subscription_id,
                    sync_state_id=sync_state_id,
                    site=(site or '').strip(),
                    sync_mode=sync_mode,
                    trigger=trigger,
                    request_id=None,
                    trace_id=trace_id,
                    created_at=now,
                ),
                False,
            )
        return (
            create_run(
                subscription_id=subscription_id,
                sync_state_id=sync_state_id,
                site=site,
                sync_mode=sync_mode,
                trigger=trigger,
                trace_id=trace_id,
            ),
            True,
        )


subscription_sync_command_event_publisher = SubscriptionSyncCommandEventPublisher()
