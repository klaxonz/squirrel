# Backward compat: tests monkeypatch get_session and crawl_task_service at module level.
# get_session is a wrapper that does dynamic attribute lookup so submodules
# that import it will still respect monkeypatching on core.database.
import core.database as _database_mod
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
