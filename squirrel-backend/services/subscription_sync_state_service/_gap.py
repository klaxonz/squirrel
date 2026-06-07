from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional


from . import get_session
from models.subscription_sync_state import SubscriptionSyncState, SyncMode
from services.subscription_sync_utils import fingerprint_head_sample, calculate_head_overlap


def record_gap_observation(
    sync_state_id: int,
    *,
    head_sample_urls: Optional[list[str]],
    anchor_found: Optional[bool],
    cursor_invalid: bool,
    cursor_loop_detected: bool,
    total_available: Optional[int],
    local_total: Optional[int],
    now: Optional[datetime] = None,
    trigger: str = 'scheduled',
    trace_id: Optional[str] = None,
) -> dict[str, int | bool]:
    from services import outbox_event_service

    current_time = now or datetime.now()
    emitted_full_request = False

    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return {'gap_suspicion_score': 0, 'emitted_full_request': False}

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

        should_request_full = (
            state.sync_mode == SyncMode.INCREMENTAL.value
            and state.gap_suspicion_score >= 8
            and (
                state.last_full_requested_at is None
                or state.last_full_requested_at <= current_time - timedelta(hours=24)
            )
        )
        if should_request_full:
            outbox_event_service.publish_event(
                event_type='full_backfill_requested',
                event_key=f'full_backfill_requested:{state.subscription_id}:{current_time.strftime("%Y%m%d")}:{state.gap_suspicion_score}',
                aggregate_type='subscription',
                aggregate_id=str(state.subscription_id),
                payload={
                    'subscription_id': state.subscription_id,
                    'sync_state_id': state.id,
                    'site': state.site,
                    'trigger': trigger,
                    'trace_id': trace_id,
                    'reason': state.gap_suspicion_reason or 'gap_suspicion',
                },
                priority='normal',
                available_at=current_time,
            )
            state.last_full_requested_at = current_time
            emitted_full_request = True

        return {
            'gap_suspicion_score': int(state.gap_suspicion_score),
            'emitted_full_request': emitted_full_request,
        }
