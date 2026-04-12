from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sys

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models import Base
from models.video import Video
from models.video_clip_marker import VideoClipMarker
from schemas.video_clip_marker import ClipMarkerCreate, ClipMarkerUpdate
from services import video_clip_marker_service


@contextmanager
def _managed_session(engine):
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _setup_test_env(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            Video.__table__,
            VideoClipMarker.__table__,
        ],
    )
    monkeypatch.setattr(video_clip_marker_service, 'get_session', lambda: _managed_session(engine))
    return engine


def _seed_video(engine, *, video_id=1, duration=120):
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            Video(
                id=video_id,
                title='Marker video',
                url='https://www.youtube.com/watch?v=clip-demo',
                domain='youtube.com',
                duration=duration,
                thumbnail='https://img.example.com/clip.jpg',
                publish_date=datetime(2024, 1, 1, 12, 0, 0),
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                updated_at=datetime(2024, 1, 1, 12, 0, 0),
                is_deleted=False,
            )
        )
        session.commit()


def test_create_update_list_and_delete_clip_marker(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_video(engine)

    created = video_clip_marker_service.create_marker(
        user_id=7,
        data=ClipMarkerCreate(
            video_id=1,
            title='Opening hook',
            note='Strong opening line',
            start_time=12.5,
            end_time=28.25,
        ),
    )

    assert created['video_id'] == 1
    assert created['title'] == 'Opening hook'
    assert created['note'] == 'Strong opening line'
    assert created['start_time'] == 12.5
    assert created['end_time'] == 28.25
    assert created['duration_seconds'] == 15.75

    listed = video_clip_marker_service.list_markers(user_id=7, video_id=1)
    assert len(listed) == 1
    assert listed[0]['id'] == created['id']

    updated = video_clip_marker_service.update_marker(
        user_id=7,
        marker_id=created['id'],
        data=ClipMarkerUpdate(
            title='Cold open',
            start_time=10,
            end_time=20,
        ),
    )

    assert updated is not None
    assert updated['title'] == 'Cold open'
    assert updated['start_time'] == 10
    assert updated['end_time'] == 20
    assert updated['duration_seconds'] == 10

    deleted_count = video_clip_marker_service.delete_marker(user_id=7, marker_id=created['id'])
    assert deleted_count == 1
    assert video_clip_marker_service.list_markers(user_id=7, video_id=1) == []


def test_create_clip_marker_uses_default_duration_and_clamps_to_video_end(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_video(engine, duration=40)

    created = video_clip_marker_service.create_marker(
        user_id=9,
        data=ClipMarkerCreate(
            video_id=1,
            title='Ending beat',
            start_time=35,
        ),
    )

    assert created['start_time'] == 35
    assert created['end_time'] == 40
    assert created['duration_seconds'] == 5


def test_create_clip_marker_rejects_inverted_range(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_video(engine)

    try:
        ClipMarkerCreate(
            video_id=1,
            start_time=30,
            end_time=10,
        )
    except ValidationError as exc:
        assert 'end_time must be greater than or equal to start_time' in str(exc)
    else:
        raise AssertionError('expected ValidationError for inverted clip range')
