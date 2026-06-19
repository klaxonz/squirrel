from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState, SyncMode

from .session import get_session


def fingerprint_head_sample(urls: list[str] | None) -> str | None:
    normalized = [str(url).strip() for url in (urls or []) if str(url).strip()]
    if not normalized:
        return None
    payload = '\n'.join(normalized[:20]).encode('utf-8')
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
) -> dict[str, int | bool | str | None]:
    """Update gap suspicion score and return whether a full backfill should be requested.

    The 24h ``last_full_requested_at`` gate on the state row prevents request storms. The subscription sync lifecycle
    owns the inflight budget check and the actual full-sync request.
    """
    current_time = now or datetime.now()

    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return {
                'gap_suspicion_score': 0,
                'should_request_full': False,
                'site': None,
                'sync_state_id': None,
            }

        previous_head_sample = list(state.last_head_sample_urls or [])
        score = int(state.gap_suspicion_score or 0)
        reasons: list[str] = []

        if anchor_found is False:
            score += 5
            state.head_anchor_missing_count += 1
            reasons.append('anchor_missing')
        elif anchor_found is True:
            score = max(0, score - 4)
            state.head_anchor_missing_count = 0

        if cursor_invalid:
            score += 5
            reasons.append('cursor_invalid')

        if cursor_loop_detected:
            score += 5
            reasons.append('cursor_loop_detected')

        overlap = calculate_head_overlap(previous_head_sample, head_sample_urls)
        if overlap is not None and overlap < 0.3:
            score += 3
            reasons.append('low_head_overlap')
        elif overlap is not None and overlap >= 0.6:
            score = max(0, score - 2)

        if total_available is not None and local_total is not None:
            drift = max(0, int(total_available) - int(local_total))
            if drift > max(20, int(local_total * 0.1)):
                score += 2
                reasons.append('total_drift')

        if state.head_anchor_missing_count >= 2 and anchor_found is False:
            score += 2
            reasons.append('repeated_anchor_missing')

        state.last_head_sample_urls = list(head_sample_urls or [])
        state.last_head_fingerprint = fingerprint_head_sample(head_sample_urls)
        state.last_known_total_available = total_available
        state.gap_suspicion_score = max(0, score)
        state.gap_suspicion_reason = ','.join(reasons) if reasons else None
        if reasons:
            state.last_gap_detected_at = current_time
        state.version += 1

        site = str(state.site or '').strip()
        sync_state_row_id = int(state.id)

        should_request_full = (
            state.sync_mode == SyncMode.INCREMENTAL.value
            and state.gap_suspicion_score >= 8
            and (
                state.last_full_requested_at is None
                or state.last_full_requested_at <= current_time - timedelta(hours=24)
            )
        )
        gap_score_snapshot = int(state.gap_suspicion_score)

    return {
        'gap_suspicion_score': gap_score_snapshot,
        'should_request_full': should_request_full,
        'site': site,
        'sync_state_id': sync_state_row_id,
    }


def mark_full_sync_requested(sync_state_id: int, *, now: datetime | None = None) -> SubscriptionSyncState | None:
    current_time = now or datetime.now()
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        state.last_full_requested_at = current_time
        state.version += 1
        return state
