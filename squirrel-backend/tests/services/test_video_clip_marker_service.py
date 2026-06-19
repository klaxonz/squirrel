from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from domains.video.application.services.engagement.clip_marker import VideoClipMarkerService
from domains.video.domain.models.video import Video
from domains.video.domain.models.video_clip_marker import VideoClipMarker
from domains.video.interfaces.dto.video_clip_marker import ClipMarkerCreate, ClipMarkerUpdate
from infrastructure.database.base import Base


@pytest.fixture
def engine():
    _engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        _engine,
        tables=[
            Video.__table__,
            VideoClipMarker.__table__,
        ],
    )
    return _engine


@pytest.fixture
def session_factory(engine):
    @contextmanager
    def _factory():
        session = Session(engine, expire_on_commit=False)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return _factory


@pytest.fixture
def svc(session_factory, tmp_path):
    return VideoClipMarkerService(
        session_factory=session_factory,
        config_settings=SimpleNamespace(clip_marker_previews_dir=tmp_path),
    )


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
            ),
        )
        session.commit()


def test_create_update_list_and_delete_clip_marker(engine, svc):
    _seed_video(engine)

    created = svc.create_marker(
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
    assert created['preview_image_url'] is None

    listed = svc.list_markers(user_id=7, video_id=1)
    assert len(listed) == 1
    assert listed[0]['id'] == created['id']

    updated = svc.update_marker(
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
    assert updated['preview_image_url'] is None

    deleted_count = svc.delete_marker(user_id=7, marker_id=created['id'])
    assert deleted_count == 1
    assert svc.list_markers(user_id=7, video_id=1) == []


def test_create_clip_marker_uses_default_duration_and_clamps_to_video_end(engine, svc):
    _seed_video(engine, duration=40)

    created = svc.create_marker(
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


def test_create_clip_marker_rejects_inverted_range(engine, svc):
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


def test_save_preview_persists_jpeg_and_returns_cache_busted_url(engine, tmp_path):
    _seed_video(engine)

    @contextmanager
    def _sf():
        session = Session(engine, expire_on_commit=False)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    svc = VideoClipMarkerService(
        session_factory=_sf,
        config_settings=SimpleNamespace(clip_marker_previews_dir=tmp_path),
    )

    created = svc.create_marker(
        user_id=7,
        data=ClipMarkerCreate(
            video_id=1,
            start_time=12,
            end_time=18,
        ),
    )

    updated = svc.save_preview(
        user_id=7,
        marker_id=created['id'],
        image_data_url='data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAX/xAAXAQEBAQEAAAAAAAAAAAAAAAABAAID/9oADAMBAAIQAxAAAAFqgP/EABQQAQAAAAAAAAAAAAAAAAAAACD/2gAIAQEAAQUCX//EABQRAQAAAAAAAAAAAAAAAAAAACD/2gAIAQMBAT8BX//EABQRAQAAAAAAAAAAAAAAAAAAACD/2gAIAQIBAT8BX//Z',
    )

    assert updated is not None
    assert updated['preview_image_url'] is not None
    assert updated['preview_image_url'].startswith('/static/clip-markers/user_7/video_1/marker_')
    assert '?v=' in updated['preview_image_url']
    assert (tmp_path / 'user_7' / 'video_1').exists()
