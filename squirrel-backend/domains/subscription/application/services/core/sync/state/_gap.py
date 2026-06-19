from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta

from sqlalchemy import func, select

from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState, SyncMode, SyncStatus
from infrastructure.config.settings import settings

from .session import get_session

logger = logging.getLogger(__name__)


def fingerprint_head_sample(urls: list[str] | None) -> str | None:
    normalized = [str(url).strip() for url in (urls or []) if str(url).strip()]
    if not normalized:
        return None
    payload = "\n".join(normalized[:20]).encode("utf-8")
    return hashlib.sha1(payload).hexdigest()


def calculate_head_overlap(previous_urls: list[str] | None, current_urls: list[str] | None) -> float | None:
    previous = {str(url).strip() for url in (previous_urls or []) if str(url).strip()}
    current = {str(url).strip() for url in (current_urls or []) if str(url).strip()}
    if not previous or not current:
        return None
    overlap = len(previous & current)
    return overlap / max(1, min(len(previous), len(current)))


def record_gap_observation(
    sync_state_id: int,
    *,
    head_sample_urls: list[str] | None,
    anchor_found: bool | None,
    cursor_invalid: bool,
    cursor_loop_detected: bool,
    total_available: int | None,
    local_total: int | None,
    now: datetime | None = None,
    trigger: str = "scheduled",
    trace_id: str | None = None,
) -> dict[str, int | bool]:
    """Update gap suspicion score for an incremental sync state and request a full backfill when it crosses threshold.

    Replaces the previous outbox-based flow: when the score crosses the threshold, we enqueue the full sync directly
    via SubscriptionSyncLifecycle.request_sync, subject to global/site inflight limits. The 24h
    ``last_full_requested_at`` gate on the state row prevents request storms; the inflight check skips the request
    when too many full syncs are already queued/running, and the next observation tick will retry naturally.
    """
    current_time = now or datetime.now()
    emitted_full_request = False

    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return {"gap_suspicion_score": 0, "emitted_full_request": False}

        previous_head_sample = list(state.last_head_sample_urls or [])
        score = int(state.gap_suspicion_score or 0)
        reasons: list[str] = []

        if anchor_found is False:
            score += 5
            state.head_anchor_missing_count += 1
            reasons.append("anchor_missing")
        elif anchor_found is True:
            score = max(0, score - 4)
            state.head_anchor_missing_count = 0

        if cursor_invalid:
            score += 5
            reasons.append("cursor_invalid")

        if cursor_loop_detected:
            score += 5
            reasons.append("cursor_loop_detected")

        overlap = calculate_head_overlap(previous_head_sample, head_sample_urls)
        if overlap is not None and overlap < 0.3:
            score += 3
            reasons.append("low_head_overlap")
        elif overlap is not None and overlap >= 0.6:
            score = max(0, score - 2)

        if total_available is not None and local_total is not None:
            drift = max(0, int(total_available) - int(local_total))
            if drift > max(20, int(local_total * 0.1)):
                score += 2
                reasons.append("total_drift")

        if state.head_anchor_missing_count >= 2 and anchor_found is False:
            score += 2
            reasons.append("repeated_anchor_missing")

        state.last_head_sample_urls = list(head_sample_urls or [])
        state.last_head_fingerprint = fingerprint_head_sample(head_sample_urls)
        state.last_known_total_available = total_available
        state.gap_suspicion_score = max(0, score)
        state.gap_suspicion_reason = ",".join(reasons) if reasons else None
        if reasons:
            state.last_gap_detected_at = current_time
        state.version += 1

        site = str(state.site or "").strip()
        subscription_id = int(state.subscription_id)
        sync_state_row_id = int(state.id)

        should_request_full = (
            state.sync_mode == SyncMode.INCREMENTAL.value
            and state.gap_suspicion_score >= 8
            and (
                state.last_full_requested_at is None
                or state.last_full_requested_at <= current_time - timedelta(hours=24)
            )
        )
        if should_request_full:
            state.last_full_requested_at = current_time

        gap_score_snapshot = int(state.gap_suspicion_score)

    # Outside the session — direct sync enqueue, subject to inflight limits.
    if should_request_full and _can_request_full_sync(site):
        emitted_full_request = _enqueue_full_backfill(
            subscription_id=subscription_id,
            site=site,
            sync_state_id=sync_state_row_id,
            trigger=trigger,
            trace_id=trace_id,
            gap_score=gap_score_snapshot,
        )

    return {
        "gap_suspicion_score": gap_score_snapshot,
        "emitted_full_request": emitted_full_request,
    }


def _can_request_full_sync(site: str) -> bool:
    """Check global/site full-sync inflight limits. Skip the request if either budget is exhausted."""
    global_limit = max(1, int(settings.FULL_SYNC_MAX_INFLIGHT))
    site_limit = max(1, int(settings.FULL_SYNC_SITE_MAX_INFLIGHT))

    with get_session() as session:
        global_inflight = int(session.execute(
            select(func.count(SubscriptionSyncState.id)).where(
                SubscriptionSyncState.sync_mode == SyncMode.FULL.value,
                SubscriptionSyncState.sync_status.in_([SyncStatus.QUEUED.value, SyncStatus.RUNNING.value]),
            ),
        ).scalar_one() or 0)
        if global_inflight >= global_limit:
            return False

        if site:
            site_inflight = int(session.execute(
                select(func.count(SubscriptionSyncState.id)).where(
                    SubscriptionSyncState.sync_mode == SyncMode.FULL.value,
                    SubscriptionSyncState.sync_status.in_([SyncStatus.QUEUED.value, SyncStatus.RUNNING.value]),
                    SubscriptionSyncState.site == site,
                ),
            ).scalar_one() or 0)
            if site_inflight >= site_limit:
                return False

    return True


def _enqueue_full_backfill(
    *,
    subscription_id: int,
    site: str,
    sync_state_id: int,
    trigger: str,
    trace_id: str | None,
    gap_score: int,
) -> bool:
    from domains.subscription.application.services.core.crud import get_subscription_by_id
    from domains.subscription.application.services.core.sync.lifecycle import SubscriptionSyncLifecycle
    from domains.subscription.application.services.core.update.models import UpdateMode, parse_trigger

    try:
        lifecycle = SubscriptionSyncLifecycle()
        subscription = get_subscription_by_id(subscription_id)
        url = (subscription.url if subscription and subscription.url else "")
        lifecycle.request_sync(
            subscription_id=subscription_id,
            url=url,
            trigger=parse_trigger(trigger),
            mode=UpdateMode.FULL,
            trace_id=trace_id,
        )
        logger.info(
            "Gap detection enqueued full backfill subscription_id=%s site=%s sync_state_id=%s gap_score=%s",
            subscription_id,
            site,
            sync_state_id,
            gap_score,
        )
        return True
    except Exception:  # gap backfill boundary — never fail the observation path
        logger.exception(
            "Failed to enqueue full backfill from gap detection subscription_id=%s sync_state_id=%s",
            subscription_id,
            sync_state_id,
        )
        return False
