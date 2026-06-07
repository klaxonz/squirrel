# Backward compat: tests monkeypatch get_session and crawl_task_service at module level.
# get_session is a wrapper that does dynamic attribute lookup so submodules
# that import it will still respect monkeypatching on core.database.
import core.database as _database_mod
from services.crawl_tasks import service as crawl_task_service  # noqa: F401
from services.subscription_sync_event_service import append_event  # noqa: F401


def get_session():
    return _database_mod.get_session()

# ruff: noqa: E402
from ._intervals import (
    INCREMENTAL_INTERVAL as INCREMENTAL_INTERVAL,
    FULL_INTERVAL as FULL_INTERVAL,
    INCREMENTAL_PENDING_THRESHOLD as INCREMENTAL_PENDING_THRESHOLD,
    RUNNING_TIMEOUT as RUNNING_TIMEOUT,
    QUEUED_RECOVERY_GRACE as QUEUED_RECOVERY_GRACE,
    SYNC_BATCH_SIZE as SYNC_BATCH_SIZE,
    MAX_DRAIN_BATCHES as MAX_DRAIN_BATCHES,
    get_mode_interval as get_mode_interval,
    build_retry_delay as build_retry_delay,
    build_success_delay as build_success_delay,
)
from ._crud import (
    _get_or_create_sync_state_in_session as _get_or_create_sync_state_in_session,
    ensure_sync_states as ensure_sync_states,
    ensure_incremental_sync_state as ensure_incremental_sync_state,
    get_sync_state as get_sync_state,
    get_sync_state_by_id as get_sync_state_by_id,
    list_due_sync_states as list_due_sync_states,
    increment_pending_video_count as increment_pending_video_count,
)
from ._transitions import (
    deactivate_sync_states as deactivate_sync_states,
    prepare_sync_state_for_enqueue as prepare_sync_state_for_enqueue,
    queue_sync_state as queue_sync_state,
    claim_sync_state as claim_sync_state,
    reconcile_task_retry_state as reconcile_task_retry_state,
    _complete_sync_success_in_session as _complete_sync_success_in_session,
    continue_full_sync_batch as continue_full_sync_batch,
    mark_sync_success as mark_sync_success,
    mark_sync_skipped as mark_sync_skipped,
    mark_sync_failed as mark_sync_failed,
    defer_sync_state as defer_sync_state,
    decrement_pending_video_count as decrement_pending_video_count,
    has_incremental_backpressure as has_incremental_backpressure,
)
from ._recovery import (
    recover_stale_sync_state as recover_stale_sync_state,
    reconcile_retry_wait_run_projections as reconcile_retry_wait_run_projections,
    reconcile_pending_video_counts as reconcile_pending_video_counts,
    reconcile_terminal_drained_sync_states as reconcile_terminal_drained_sync_states,
    recover_stale_queued_sync_states as recover_stale_queued_sync_states,
    recover_stale_running_sync_states as recover_stale_running_sync_states,
    _scan_pending_video_counts as _scan_pending_video_counts,
    _scan_subscription_update_state_ids as _scan_subscription_update_state_ids,
)
from ._stale import (
    _recover_stale_running_states_in_session as _recover_stale_running_states_in_session,
    _recover_stale_running_state as _recover_stale_running_state,
    _can_complete_drained_state as _can_complete_drained_state,
)
from ._events import (
    _append_recovery_run_events as _append_recovery_run_events,
    _append_terminal_reconcile_run_events as _append_terminal_reconcile_run_events,
    _append_state_event as _append_state_event,
    _get_latest_state_run_projection as _get_latest_state_run_projection,
)
from ._gap import record_gap_observation as record_gap_observation
from ._utils import build_queue_token as build_queue_token, attach_sync_fields as attach_sync_fields
