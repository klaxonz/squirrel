# Backward compat: tests monkeypatch get_session and crawl_task_service at module level.
# get_session is a wrapper that does dynamic attribute lookup so submodules
# that import it will still respect monkeypatching on core.database.
from datetime import datetime

import core.database as _database_mod
from models.subscription_sync_state import SubscriptionSyncState
from services.crawl_tasks import service as crawl_task_service  # noqa: F401
from services.subscription_sync_event_service import append_event  # noqa: F401


def get_session():
    return _database_mod.get_session()


# ruff: noqa: E402
from ._crud import (
    _get_or_create_sync_state_in_session as _get_or_create_sync_state_in_session,
)
from ._crud import (
    ensure_incremental_sync_state as ensure_incremental_sync_state,
)
from ._crud import (
    ensure_sync_states as ensure_sync_states,
)
from ._crud import (
    get_sync_state as get_sync_state,
)
from ._crud import (
    get_sync_state_by_id as get_sync_state_by_id,
)
from ._crud import (
    increment_pending_video_count as increment_pending_video_count,
)
from ._crud import (
    list_due_sync_states as list_due_sync_states,
)
from ._events import (
    _append_recovery_run_events as _append_recovery_run_events,
)
from ._events import (
    _append_state_event as _append_state_event,
)
from ._events import (
    _append_terminal_reconcile_run_events as _append_terminal_reconcile_run_events,
)
from ._events import (
    _get_latest_state_run_projection as _get_latest_state_run_projection,
)
from ._gap import record_gap_observation as record_gap_observation
from ._intervals import (
    FULL_INTERVAL as FULL_INTERVAL,
)
from ._intervals import (
    INCREMENTAL_INTERVAL as INCREMENTAL_INTERVAL,
)
from ._intervals import (
    INCREMENTAL_PENDING_THRESHOLD as INCREMENTAL_PENDING_THRESHOLD,
)
from ._intervals import (
    MAX_DRAIN_BATCHES as MAX_DRAIN_BATCHES,
)
from ._intervals import (
    QUEUED_RECOVERY_GRACE as QUEUED_RECOVERY_GRACE,
)
from ._intervals import (
    RUNNING_TIMEOUT as RUNNING_TIMEOUT,
)
from ._intervals import (
    SYNC_BATCH_SIZE as SYNC_BATCH_SIZE,
)
from ._intervals import (
    build_retry_delay as build_retry_delay,
)
from ._intervals import (
    build_success_delay as build_success_delay,
)
from ._intervals import (
    get_mode_interval as get_mode_interval,
)
from ._recovery import (
    _scan_pending_video_counts as _scan_pending_video_counts,
)
from ._recovery import (
    _scan_subscription_update_state_ids as _scan_subscription_update_state_ids,
)
from ._recovery import (
    reconcile_pending_video_counts as reconcile_pending_video_counts,
)
from ._recovery import (
    reconcile_retry_wait_run_projections as reconcile_retry_wait_run_projections,
)
from ._recovery import (
    reconcile_terminal_drained_sync_states as reconcile_terminal_drained_sync_states,
)
from ._recovery import (
    recover_stale_queued_sync_states as recover_stale_queued_sync_states,
)
from ._recovery import (
    recover_stale_running_sync_states as recover_stale_running_sync_states,
)
from ._recovery import (
    recover_stale_sync_state as recover_stale_sync_state,
)
from ._stale import (
    _can_complete_drained_state as _can_complete_drained_state,
)
from ._stale import (
    _recover_stale_running_state as _recover_stale_running_state,
)
from ._stale import (
    _recover_stale_running_states_in_session as _recover_stale_running_states_in_session,
)
from ._transitions import (
    _complete_sync_success_in_session as _complete_sync_success_in_session,
)
from ._transitions import (
    claim_sync_state as claim_sync_state,
)
from ._transitions import (
    continue_full_sync_batch as continue_full_sync_batch,
)
from ._transitions import (
    deactivate_sync_states as deactivate_sync_states,
)
from ._transitions import (
    decrement_pending_video_count as decrement_pending_video_count,
)
from ._transitions import (
    defer_sync_state as defer_sync_state,
)
from ._transitions import (
    has_incremental_backpressure as has_incremental_backpressure,
)
from ._transitions import (
    mark_sync_failed as mark_sync_failed,
)
from ._transitions import (
    mark_sync_skipped as mark_sync_skipped,
)
from ._transitions import (
    mark_sync_success as mark_sync_success,
)
from ._transitions import (
    prepare_sync_state_for_enqueue as prepare_sync_state_for_enqueue,
)
from ._transitions import (
    queue_sync_state as queue_sync_state,
)
from ._transitions import (
    reconcile_task_retry_state as reconcile_task_retry_state,
)
from ._utils import attach_sync_fields as attach_sync_fields
from ._utils import build_queue_token as build_queue_token


class SyncStateService:
    def __init__(self, session_factory=get_session):
        self.session_factory = session_factory

    def ensure_sync_states(self, subscription_id: int, url: str | None) -> dict[str, SubscriptionSyncState]:
        return ensure_sync_states(subscription_id, url)

    def ensure_incremental_sync_state(self, subscription_id: int, url: str | None) -> SubscriptionSyncState:
        return ensure_incremental_sync_state(subscription_id, url)

    def get_sync_state(self, subscription_id: int, mode: str) -> SubscriptionSyncState | None:
        return get_sync_state(subscription_id, mode)

    def get_sync_state_by_id(self, sync_state_id: int) -> SubscriptionSyncState | None:
        return get_sync_state_by_id(sync_state_id)

    def list_due_sync_states(
        self,
        mode: str,
        limit: int = SYNC_BATCH_SIZE,
        *,
        now: datetime | None = None,
    ) -> list[tuple[SubscriptionSyncState, str]]:
        return list_due_sync_states(mode, limit=limit, now=now)

    def increment_pending_video_count(self, sync_state_id: int | None, count: int = 1) -> None:
        return increment_pending_video_count(sync_state_id, count=count)

    def record_gap_observation(self, *args, **kwargs):
        return record_gap_observation(*args, **kwargs)

    def reconcile_pending_video_counts(self, *args, **kwargs):
        return reconcile_pending_video_counts(*args, **kwargs)

    def reconcile_retry_wait_run_projections(self, *args, **kwargs):
        return reconcile_retry_wait_run_projections(*args, **kwargs)

    def reconcile_terminal_drained_sync_states(self, *args, **kwargs):
        return reconcile_terminal_drained_sync_states(*args, **kwargs)

    def recover_stale_queued_sync_states(self, *args, **kwargs):
        return recover_stale_queued_sync_states(*args, **kwargs)

    def recover_stale_running_sync_states(self, *args, **kwargs):
        return recover_stale_running_sync_states(*args, **kwargs)

    def recover_stale_sync_state(self, *args, **kwargs):
        return recover_stale_sync_state(*args, **kwargs)

    def claim_sync_state(self, *args, **kwargs):
        return claim_sync_state(*args, **kwargs)

    def continue_full_sync_batch(self, *args, **kwargs):
        return continue_full_sync_batch(*args, **kwargs)

    def deactivate_sync_states(self, subscription_id: int, reason: str = 'manual_unsubscribe'):
        return deactivate_sync_states(subscription_id, reason=reason)

    def decrement_pending_video_count(self, *args, **kwargs):
        return decrement_pending_video_count(*args, **kwargs)

    def defer_sync_state(self, *args, **kwargs):
        return defer_sync_state(*args, **kwargs)

    def has_incremental_backpressure(self, *args, **kwargs) -> bool:
        return has_incremental_backpressure(*args, **kwargs)

    def mark_sync_failed(self, *args, **kwargs):
        return mark_sync_failed(*args, **kwargs)

    def mark_sync_skipped(self, *args, **kwargs):
        return mark_sync_skipped(*args, **kwargs)

    def mark_sync_success(self, *args, **kwargs):
        return mark_sync_success(*args, **kwargs)

    def prepare_sync_state_for_enqueue(self, *args, **kwargs):
        return prepare_sync_state_for_enqueue(*args, **kwargs)

    def queue_sync_state(self, *args, **kwargs):
        return queue_sync_state(*args, **kwargs)

    def reconcile_task_retry_state(self, *args, **kwargs):
        return reconcile_task_retry_state(*args, **kwargs)

    def attach_sync_fields(self, *args, **kwargs):
        return attach_sync_fields(*args, **kwargs)

    def build_queue_token(self, *args, **kwargs):
        return build_queue_token(*args, **kwargs)


_default = SyncStateService()
