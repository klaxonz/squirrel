import logging
from collections.abc import Callable, Iterable
from datetime import datetime

from sqlalchemy import select

from domains.subscription.application.services.core.sync.lifecycle import (
    SubscriptionSyncLifecycle,
    SubscriptionSyncTarget,
)
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from infrastructure.database.session import get_session

from .models import (
    SubscriptionDirectRunResult,
    SubscriptionScheduleResult,
    UpdateMode,
    UpdateTrigger,
)

logger = logging.getLogger(__name__)


class SubscriptionScheduler:
    """Subscription update scheduler."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session
        self.lifecycle = SubscriptionSyncLifecycle(session_factory=session_factory)

    def schedule_one(
        self,
        subscription_id: int,
        url: str,
        trigger: UpdateTrigger = UpdateTrigger.MANUAL,
        mode: UpdateMode = UpdateMode.INCREMENTAL,
        user_id: int | None = None,
        force: bool = False,
        trace_id: str | None = None,
        run_id: str | None = None,
    ) -> SubscriptionScheduleResult:
        return self.lifecycle.request_sync(
            subscription_id=subscription_id,
            url=url,
            trigger=trigger,
            mode=mode,
            user_id=user_id,
            force=force,
            trace_id=trace_id,
            run_id=run_id,
        )

    def run_one_inline(
        self,
        subscription_id: int,
        url: str,
        trigger: UpdateTrigger = UpdateTrigger.MANUAL,
        mode: UpdateMode = UpdateMode.INCREMENTAL,
        user_id: int | None = None,
        force: bool = False,
        trace_id: str | None = None,
        run_id: str | None = None,
    ) -> SubscriptionDirectRunResult:
        return self.lifecycle.run_inline_sync(
            subscription_id=subscription_id,
            url=url,
            trigger=trigger,
            mode=mode,
            user_id=user_id,
            force=force,
            trace_id=trace_id,
            run_id=run_id,
        )

    def schedule_batch(
        self,
        subscription_ids: list[int],
        trigger: UpdateTrigger = UpdateTrigger.SCHEDULED,
    ) -> tuple[int, int]:
        success_count = 0
        error_count = 0

        with self.session_factory() as session:
            rows = session.execute(
                select(UserSubscription.subscription_id)
                .where(
                    UserSubscription.subscription_id.in_(subscription_ids),
                    UserSubscription.is_deleted.is_(False),
                ),
            ).all()
            ids = [row[0] for row in rows]

        if ids:
            url_rows = self._batch_get_subscription_urls(ids)
            url_map = dict(url_rows)
        else:
            url_map = {}

        for subscription_id in ids:
            url = url_map.get(subscription_id, '')
            scheduled = self.schedule_one(subscription_id, url, trigger)
            if scheduled.status == "queued":
                success_count += 1
            elif scheduled.status == "failed":
                error_count += 1

        return success_count, error_count

    def enqueue_all_active(
        self,
        trigger: UpdateTrigger = UpdateTrigger.SCHEDULED,
        mode: UpdateMode = UpdateMode.INCREMENTAL,
    ) -> tuple[int, int]:
        resolved_mode = self._resolve_mode(mode)
        targets = (
            SubscriptionSyncTarget(subscription_id=subscription_id, url=url)
            for subscription_id, url in self._list_due_active_subscriptions(resolved_mode)
        )
        return self._dispatch_due_targets(
            targets=targets,
            mode=resolved_mode,
            action_name="enqueue",
            action=lambda target: self._schedule_due_target(target=target, trigger=trigger, mode=resolved_mode),
        )

    def enqueue_due_states(
        self,
        trigger: UpdateTrigger = UpdateTrigger.SCHEDULED,
        mode: UpdateMode = UpdateMode.INCREMENTAL,
        *,
        now: datetime | None = None,
        limit: int | None = None,
    ) -> tuple[int, int]:
        resolved_mode = self._resolve_mode(mode)
        current_time = now or datetime.now()
        targets = self.lifecycle.list_due_sync_targets(
            resolved_mode,
            limit=limit,
            now=current_time,
        )
        return self._dispatch_due_targets(
            targets=targets,
            mode=resolved_mode,
            action_name="emit",
            action=lambda target: self._emit_due_sync_event(
                target=target,
                trigger=trigger,
                mode=resolved_mode,
            ),
        )

    def _dispatch_due_targets(
        self,
        *,
        targets: Iterable[SubscriptionSyncTarget],
        mode: UpdateMode,
        action_name: str,
        action: Callable[[SubscriptionSyncTarget], str],
    ) -> tuple[int, int]:
        success_count = 0
        error_count = 0

        for target in targets:
            try:
                action_result = action(target)
                if action_result == "success":
                    success_count += 1
                elif action_result == "failed":
                    error_count += 1
            except Exception:  # dispatch boundary — count error and continue
                error_count += 1
                logger.exception(
                    "Failed to %s due sync target subscription_id=%s sync_state_id=%s mode=%s",
                    action_name,
                    target.subscription_id,
                    target.sync_state_id,
                    mode.value,
                )

        logger.info(
            "Due sync %s completed: success=%s failed=%s mode=%s",
            action_name,
            success_count,
            error_count,
            mode.value,
        )
        return success_count, error_count

    def _schedule_due_target(
        self,
        *,
        target: SubscriptionSyncTarget,
        trigger: UpdateTrigger,
        mode: UpdateMode,
    ) -> str:
        scheduled = self.schedule_one(
            subscription_id=target.subscription_id,
            url=target.url,
            trigger=trigger,
            mode=mode,
        )
        if scheduled.status == "queued":
            return "success"
        if scheduled.status == "failed":
            return "failed"
        return "skipped"

    def _emit_due_sync_event(
        self,
        *,
        target: SubscriptionSyncTarget,
        trigger: UpdateTrigger,
        mode: UpdateMode,
    ) -> str:
        if target.sync_state_id is None:
            return "skipped"

        scheduled = self.lifecycle.request_sync(
            subscription_id=target.subscription_id,
            url=target.url,
            trigger=trigger,
            mode=mode,
        )
        if scheduled.status == "queued":
            return "success"
        if scheduled.status == "failed":
            return "failed"
        return "skipped"

    def _list_due_active_subscriptions(self, mode: UpdateMode) -> list[tuple[int, str]]:
        now = datetime.now()

        with self.session_factory() as session:
            rows = session.execute(
                select(Subscription.id, Subscription.url)
                .where(
                    Subscription.is_deleted.is_(False),
                    Subscription.url.is_not(None),
                )
                .where(
                    select(UserSubscription.id)
                    .where(
                        UserSubscription.subscription_id == Subscription.id,
                        UserSubscription.is_deleted.is_(False),
                    )
                    .exists(),
                )
                .order_by(Subscription.id.asc()),
            ).all()

        if not rows:
            return []

        sub_ids = [row[0] for row in rows]
        url_map = {row[0]: row[1] for row in rows}

        from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState

        with self.session_factory() as session:
            state_rows = session.execute(
                select(SubscriptionSyncState)
                .where(
                    SubscriptionSyncState.subscription_id.in_(sub_ids),
                    SubscriptionSyncState.sync_mode == mode.value,
                ),
            ).scalars().all()

        state_map: dict[int, SubscriptionSyncState] = {s.subscription_id: s for s in state_rows}

        due_subscriptions: list[tuple[int, str]] = []
        for subscription_id in sub_ids:
            sync_state = state_map.get(subscription_id)
            if sync_state is None:
                due_subscriptions.append((subscription_id, url_map[subscription_id]))
                continue

            sync_status = getattr(sync_state, "sync_status", None)
            if sync_status in {"queued", "running"}:
                continue

            next_sync_at = getattr(sync_state, "next_sync_at", None)
            if next_sync_at is None or next_sync_at <= now:
                due_subscriptions.append((subscription_id, url_map[subscription_id]))

        return due_subscriptions

    @staticmethod
    def _resolve_mode(mode: UpdateMode) -> UpdateMode:
        if mode == UpdateMode.FULL:
            return UpdateMode.FULL
        return UpdateMode.INCREMENTAL

    def _batch_get_subscription_urls(self, subscription_ids: list[int]) -> list[tuple[int, str]]:
        from sqlalchemy import select

        from domains.subscription.domain.models.subscription import Subscription

        with self.session_factory() as session:
            rows = session.execute(
                select(Subscription.id, Subscription.url)
                .where(Subscription.id.in_(subscription_ids)),
            ).all()
            return [(row[0], row[1] or '') for row in rows]


scheduler = SubscriptionScheduler()
