from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from domains.video.domain.models.video_history import VideoHistory
from domains.video.interfaces.dto.video_history import HistoryCreate


def resolve_reported_at(report: HistoryCreate) -> datetime:
    raw_timestamp = report.timestamp
    if raw_timestamp is None:
        return datetime.now()

    seconds = raw_timestamp / 1000 if raw_timestamp > 1_000_000_000_000 else raw_timestamp
    return datetime.fromtimestamp(seconds)


def is_newer_report(
    candidate: HistoryCreate,
    current: HistoryCreate,
    *,
    candidate_index: int,
    current_index: int,
) -> bool:
    if candidate.timestamp is not None and current.timestamp is not None:
        candidate_reported_at = resolve_reported_at(candidate)
        current_reported_at = resolve_reported_at(current)
        if candidate_reported_at != current_reported_at:
            return candidate_reported_at > current_reported_at
        if candidate.last_position != current.last_position:
            return candidate.last_position >= current.last_position

    return candidate_index >= current_index


def normalize_history_reports(reports: Iterable[HistoryCreate]) -> list[HistoryCreate]:
    latest_by_video_id: dict[int, tuple[HistoryCreate, int]] = {}
    for index, report in enumerate(reports):
        current = latest_by_video_id.get(report.video_id)
        if current is None or is_newer_report(
            report,
            current[0],
            candidate_index=index,
            current_index=current[1],
        ):
            latest_by_video_id[report.video_id] = (report, index)
    return [item[0] for item in latest_by_video_id.values()]


def apply_history_updates(session: Session, user_id: int, reports: list[HistoryCreate]) -> None:
    normalized_reports = normalize_history_reports(reports)
    if not normalized_reports:
        return

    video_ids = [report.video_id for report in normalized_reports]
    existing_histories = session.scalars(
        select(VideoHistory)
        .where(
            VideoHistory.user_id == user_id,
            VideoHistory.video_id.in_(video_ids),
        )
        .order_by(VideoHistory.video_id.asc(), VideoHistory.end_time.desc(), VideoHistory.id.desc()),
    ).all()

    histories_by_video_id: dict[int, list[VideoHistory]] = {}
    for history in existing_histories:
        histories_by_video_id.setdefault(history.video_id, []).append(history)

    for report in normalized_reports:
        histories = histories_by_video_id.get(report.video_id, [])
        reported_at = resolve_reported_at(report)

        if histories:
            history = histories[0]
            duplicate_ids = [item.id for item in histories[1:]]
            if duplicate_ids:
                session.execute(
                    delete(VideoHistory).where(VideoHistory.id.in_(duplicate_ids)),
                )

            existing_end_time = history.end_time or history.updated_at or history.created_at or reported_at
            if reported_at < existing_end_time and report.last_position <= history.last_position:
                continue

            history.watch_duration += 0
            history.last_position = report.last_position
            history.end_time = max(reported_at, existing_end_time)
            continue

        session.add(
            VideoHistory(
                user_id=user_id,
                video_id=report.video_id,
                start_time=reported_at,
                end_time=reported_at,
                duration=0,
                watch_duration=0,
                last_position=report.last_position,
            ),
        )
