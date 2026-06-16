from contextlib import contextmanager
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from domains.playlist.application.services.commands import PlaylistCommandService
from domains.playlist.application.services.playback import PlaylistPlaybackService
from domains.playlist.application.services.queries import PlaylistQueryService
from domains.playlist.domain.models.playlist import Playlist
from domains.playlist.domain.models.playlist_item import PlaylistItem
from domains.playlist.interfaces.dto.playlist import PlaylistItemReorder
from domains.video.domain.models.video import Video
from shared_kernel.domain.base import Base


@pytest.fixture
def engine():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            Playlist.__table__,
            PlaylistItem.__table__,
            Video.__table__,
        ],
    )
    return engine


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
def command_svc(session_factory):
    return PlaylistCommandService(session_factory=session_factory)


@pytest.fixture
def query_svc(session_factory):
    return PlaylistQueryService(session_factory=session_factory)


@pytest.fixture
def playback_svc(session_factory):
    return PlaylistPlaybackService(session_factory=session_factory)


def _seed_videos(engine):
    now = datetime(2026, 6, 1, 12, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Video(id=1, title='One', url='https://example.com/1', is_deleted=False, created_at=now, updated_at=now),
            Video(id=2, title='Two', url='https://example.com/2', is_deleted=False, created_at=now, updated_at=now),
            Video(id=3, title='Three', url='https://example.com/3', is_deleted=False, created_at=now, updated_at=now),
        ])
        session.commit()


def test_add_video_without_playlist_creates_default_and_deduplicates(engine, command_svc, query_svc):
    _seed_videos(engine)

    first = command_svc.add_video_to_playlist(user_id=7, video_id=1)
    second = command_svc.add_video_to_playlist(user_id=7, video_id=1)
    default_playlist = query_svc.get_default_playlist(user_id=7)

    assert first['id'] == second['id']
    assert first['position'] == 1
    assert default_playlist is not None
    assert default_playlist['name'] == '稍后再看'
    assert default_playlist['video_count'] == 1


def test_reorder_playlist_item_shifts_neighbor_positions(engine, command_svc, query_svc):
    _seed_videos(engine)
    playlist = command_svc.add_video_to_playlist(user_id=7, video_id=1)
    playlist_id = playlist['playlist_id']
    command_svc.add_video_to_playlist(user_id=7, video_id=2, playlist_id=playlist_id)
    command_svc.add_video_to_playlist(user_id=7, video_id=3, playlist_id=playlist_id)

    moved = command_svc.reorder_playlist_item(
        user_id=7,
        data=PlaylistItemReorder(playlist_id=playlist_id, video_id=1, new_position=3),
    )
    items = query_svc.get_playlist_items(user_id=7, playlist_id=playlist_id)

    assert moved is not None
    assert moved['position'] == 3
    assert [(item['video_id'], item['position']) for item in items] == [(2, 1), (3, 2), (1, 3)]


def test_remove_video_compacts_positions(engine, command_svc, query_svc):
    _seed_videos(engine)
    first = command_svc.add_video_to_playlist(user_id=7, video_id=1)
    playlist_id = first['playlist_id']
    command_svc.add_video_to_playlist(user_id=7, video_id=2, playlist_id=playlist_id)
    command_svc.add_video_to_playlist(user_id=7, video_id=3, playlist_id=playlist_id)

    removed = command_svc.remove_video_from_playlist(user_id=7, playlist_id=playlist_id, video_id=2)
    items = query_svc.get_playlist_items(user_id=7, playlist_id=playlist_id)

    assert removed is True
    assert [(item['video_id'], item['position']) for item in items] == [(1, 1), (3, 2)]


def test_play_next_video_wraps_to_first_item(engine, command_svc, playback_svc):
    _seed_videos(engine)
    first = command_svc.add_video_to_playlist(user_id=7, video_id=1)
    playlist_id = first['playlist_id']
    command_svc.add_video_to_playlist(user_id=7, video_id=2, playlist_id=playlist_id)
    command_svc.add_video_to_playlist(user_id=7, video_id=3, playlist_id=playlist_id)

    result = playback_svc.play_next_video(user_id=7, playlist_id=playlist_id, video_id=3)

    assert result == {
        'has_next': True,
        'video_id': 1,
        'video': result['video'],
    }
    assert result['video']['id'] == 1


def test_default_playlist_cannot_be_modified_or_deleted(engine, command_svc):
    _seed_videos(engine)
    item = command_svc.add_video_to_playlist(user_id=7, video_id=1)

    with pytest.raises(ValueError, match='Cannot delete default playlist'):
        command_svc.delete_playlist(user_id=7, playlist_id=item['playlist_id'])
