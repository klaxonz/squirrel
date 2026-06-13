from __future__ import annotations

from datetime import timedelta

from models.subscription_sync_state import SyncMode

INCREMENTAL_INTERVAL = timedelta(minutes=5)
FULL_INTERVAL = timedelta(hours=2)
INCREMENTAL_PENDING_THRESHOLD = 15
RUNNING_TIMEOUT = timedelta(minutes=30)
QUEUED_RECOVERY_GRACE = timedelta(minutes=2)
SYNC_BATCH_SIZE = 200
MAX_DRAIN_BATCHES = 20


def get_mode_interval(mode: str) -> timedelta:
    if mode == SyncMode.FULL.value:
        return FULL_INTERVAL
    return INCREMENTAL_INTERVAL


def build_retry_delay(mode: str, failure_count: int) -> timedelta:
    if mode == SyncMode.FULL.value:
        minutes = min(30 * (2 ** max(failure_count - 1, 0)), 24 * 60)
        return timedelta(minutes=minutes)
    minutes = min(5 * (2 ** max(failure_count - 1, 0)), 6 * 60)
    return timedelta(minutes=minutes)


def build_success_delay(mode: str, idle_sync_count: int, videos_found: int) -> timedelta:
    if mode == SyncMode.FULL.value:
        if videos_found > 0:
            return FULL_INTERVAL
        minutes = min(int(FULL_INTERVAL.total_seconds() / 60) * (2 ** min(idle_sync_count, 3)), 24 * 60)
        return timedelta(minutes=minutes)

    if videos_found > 0:
        return INCREMENTAL_INTERVAL
    base_minutes = 15
    minutes = min(base_minutes * (2 ** min(idle_sync_count, 4)), 6 * 60)
    return timedelta(minutes=minutes)
