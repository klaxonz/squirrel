from __future__ import annotations


ACTIVE_EXTRACTION_PHASES = {'extracting', 'finalizing', 'completed'}
TERMINAL_STATUSES = {'success', 'failed', 'deferred', 'timeout'}


def is_feed_completed(current_phase: str | None, status: str | None) -> bool:
    normalized_phase = str(current_phase or '').strip().lower()
    normalized_status = str(status or '').strip().lower()
    return normalized_phase in ACTIVE_EXTRACTION_PHASES or normalized_status in TERMINAL_STATUSES


def build_progress_snapshot(
    *,
    status: str | None,
    current_phase: str | None,
    videos_found: int = 0,
    videos_enqueued: int = 0,
    videos_extracted: int = 0,
    pending_video_count: int = 0,
) -> dict[str, int | str | bool]:
    normalized_status = str(status or '').strip().lower()
    normalized_phase = str(current_phase or '').strip().lower()
    enqueued_total = max(int(videos_enqueued or 0), int(videos_extracted or 0) + int(pending_video_count or 0))
    extracted_total = min(max(int(videos_extracted or 0), 0), enqueued_total) if enqueued_total else max(int(videos_extracted or 0), 0)
    feed_completed = is_feed_completed(normalized_phase, normalized_status)

    if normalized_status == 'queued':
        percent = 0
        label = '排队中'
    elif enqueued_total > 0 and feed_completed:
        percent = min(100, round((extracted_total / enqueued_total) * 100))
        label = f'{extracted_total} / {enqueued_total}'
    elif normalized_phase == 'finalizing':
        percent = 92
        label = '收尾中'
    elif normalized_phase == 'enqueueing':
        percent = 70
        label = f'已入队 {int(videos_enqueued or 0)}'
    elif normalized_phase == 'calculating_delta':
        percent = 45
        label = f'已发现 {int(videos_found or 0)}'
    elif normalized_phase == 'fetching_feed':
        percent = 18
        label = '拉取列表中'
    elif normalized_status == 'success':
        percent = 100
        label = f'{extracted_total} / {enqueued_total}' if enqueued_total > 0 else '已完成'
    elif normalized_status == 'failed':
        percent = 100
        label = '失败'
    else:
        percent = 0
        label = '等待开始'

    return {
        'feed_completed': feed_completed,
        'progress_percent': percent,
        'progress_label': label,
    }
