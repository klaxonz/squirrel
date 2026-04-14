import base64
from pathlib import Path

from sqlalchemy import select

from core.config import settings
from core.database import get_session
from models.video import Video
from models.video_clip_marker import VideoClipMarker
from schemas.video_clip_marker import ClipMarkerCreate, ClipMarkerUpdate

DEFAULT_CLIP_DURATION_SECONDS = 15.0


def _clip_marker_previews_dir() -> Path:
    return settings.clip_marker_previews_dir


def _serialize_preview_url(marker: VideoClipMarker) -> str | None:
    preview_url = getattr(marker, 'preview_image_url', None)
    if not preview_url:
        return None

    version_source = marker.updated_at or marker.created_at
    if not version_source:
        return preview_url

    version = int(version_source.timestamp() * 1000)
    separator = '&' if '?' in preview_url else '?'
    return f'{preview_url}{separator}v={version}'


def serialize_marker(marker: VideoClipMarker) -> dict:
    payload = marker.to_dict()
    payload['duration_seconds'] = round(max((marker.end_time or 0) - (marker.start_time or 0), 0), 3)
    payload['preview_image_url'] = _serialize_preview_url(marker)
    return payload


def _resolve_preview_file_path(marker: VideoClipMarker) -> Path:
    return (
        _clip_marker_previews_dir()
        / f'user_{marker.user_id}'
        / f'video_{marker.video_id}'
        / f'marker_{marker.id}.jpg'
    )


def _remove_preview_file(marker: VideoClipMarker) -> None:
    preview_path = _resolve_preview_file_path(marker)
    if preview_path.exists():
        preview_path.unlink()

    parent = preview_path.parent
    while parent != _clip_marker_previews_dir() and parent.exists():
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def _decode_preview_image(data_url: str) -> bytes:
    try:
        encoded = data_url.split(',', 1)[1]
    except IndexError as exc:
        raise ValueError('Invalid image_data_url') from exc

    try:
        return base64.b64decode(encoded, validate=True)
    except ValueError as exc:
        raise ValueError('Invalid image_data_url') from exc


def _get_video_or_raise(session, video_id: int) -> Video:
    video = session.get(Video, video_id)
    if not video or getattr(video, 'is_deleted', False):
        raise ValueError('Video not found')
    return video


def _normalize_bounds(start_time: float, end_time: float | None, video_duration: float | int | None) -> tuple[float, float]:
    normalized_start = max(float(start_time or 0), 0.0)
    duration_limit = float(video_duration or 0) if video_duration is not None else 0.0

    if duration_limit > 0:
        normalized_start = min(normalized_start, duration_limit)

    if end_time is None:
        normalized_end = normalized_start + DEFAULT_CLIP_DURATION_SECONDS
    else:
        normalized_end = max(float(end_time), 0.0)

    if duration_limit > 0:
        normalized_end = min(normalized_end, duration_limit)

    if normalized_end < normalized_start:
        raise ValueError('end_time must be greater than or equal to start_time')

    return round(normalized_start, 3), round(normalized_end, 3)


def list_markers(user_id: int, video_id: int) -> list[dict]:
    with get_session() as session:
        markers = session.scalars(
            select(VideoClipMarker)
            .where(
                VideoClipMarker.user_id == user_id,
                VideoClipMarker.video_id == video_id,
            )
            .order_by(VideoClipMarker.start_time.asc(), VideoClipMarker.created_at.asc(), VideoClipMarker.id.asc())
        ).all()
        return [serialize_marker(marker) for marker in markers]


def create_marker(user_id: int, data: ClipMarkerCreate) -> dict:
    with get_session() as session:
        video = _get_video_or_raise(session, data.video_id)
        start_time, end_time = _normalize_bounds(data.start_time, data.end_time, video.duration)

        marker = VideoClipMarker(
            user_id=user_id,
            video_id=data.video_id,
            title=data.title,
            note=data.note,
            start_time=start_time,
            end_time=end_time,
        )
        session.add(marker)
        session.commit()
        session.refresh(marker)
        return serialize_marker(marker)


def update_marker(user_id: int, marker_id: int, data: ClipMarkerUpdate) -> dict | None:
    with get_session() as session:
        marker = session.scalar(
            select(VideoClipMarker).where(
                VideoClipMarker.id == marker_id,
                VideoClipMarker.user_id == user_id,
            )
        )
        if not marker:
            return None

        video = _get_video_or_raise(session, marker.video_id)
        field_names = data.model_fields_set

        if 'title' in field_names:
            marker.title = data.title
        if 'note' in field_names:
            marker.note = data.note

        next_start_time = data.start_time if 'start_time' in field_names else marker.start_time
        next_end_time = data.end_time if 'end_time' in field_names else marker.end_time
        marker.start_time, marker.end_time = _normalize_bounds(next_start_time, next_end_time, video.duration)

        session.commit()
        session.refresh(marker)
        return serialize_marker(marker)


def save_preview(user_id: int, marker_id: int, image_data_url: str) -> dict | None:
    preview_bytes = _decode_preview_image(image_data_url)

    with get_session() as session:
        marker = session.scalar(
            select(VideoClipMarker).where(
                VideoClipMarker.id == marker_id,
                VideoClipMarker.user_id == user_id,
            )
        )
        if not marker:
            return None

        preview_path = _resolve_preview_file_path(marker)
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_bytes(preview_bytes)

        marker.preview_image_url = (
            f'/static/clip-markers/user_{marker.user_id}/video_{marker.video_id}/marker_{marker.id}.jpg'
        )
        session.commit()
        session.refresh(marker)
        return serialize_marker(marker)


def delete_marker(user_id: int, marker_id: int) -> int:
    with get_session() as session:
        marker = session.scalar(
            select(VideoClipMarker).where(
                VideoClipMarker.id == marker_id,
                VideoClipMarker.user_id == user_id,
            )
        )
        if not marker:
            return 0

        _remove_preview_file(marker)
        session.delete(marker)
        session.commit()
        return 1
