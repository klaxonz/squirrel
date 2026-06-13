from __future__ import annotations

from uuid import uuid4

from models.subscription_sync_state import SubscriptionSyncState, SyncStatus


def build_queue_token() -> str:
    return uuid4().hex


def attach_sync_fields(target: dict, sync_state: SubscriptionSyncState | None) -> dict:
    if not sync_state:
        target.setdefault("sync_status", SyncStatus.IDLE.value)
        target.setdefault("last_sync_at", "")
        target.setdefault("last_success_at", "")
        target.setdefault("next_sync_at", "")
        target.setdefault("last_error", "")
        target.setdefault("pending_video_count", 0)
        return target

    target["sync_status"] = sync_state.sync_status
    target["last_sync_at"] = sync_state.last_sync_at.strftime("%Y-%m-%d %H:%M:%S") if sync_state.last_sync_at else ""
    target["last_success_at"] = sync_state.last_success_at.strftime("%Y-%m-%d %H:%M:%S") if sync_state.last_success_at else ""
    target["next_sync_at"] = sync_state.next_sync_at.strftime("%Y-%m-%d %H:%M:%S") if sync_state.next_sync_at else ""
    target["last_error"] = sync_state.last_error or ""
    target["pending_video_count"] = sync_state.pending_video_count
    return target
