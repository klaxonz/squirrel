from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sys
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crawl import PluginInvokeResponse
from models import Base
from models.video import Video
from services import video_service


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
    Base.metadata.create_all(engine, tables=[Video.__table__])
    monkeypatch.setattr(video_service, 'get_session', lambda: _managed_session(engine))
    monkeypatch.setattr(video_service.redis_client, 'get', lambda key: None)
    monkeypatch.setattr(video_service.redis_client, 'setex', lambda key, ttl, value: None)
    monkeypatch.setattr(
        video_service.SiteCatalog,
        'find_site_by_domain',
        lambda domain: ('bilibili', {'metadata': {}}),
    )
    return engine


def _seed_video(engine, *, video_id=1, url='https://www.bilibili.com/video/BV1xx411c7mD'):
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            Video(
                id=video_id,
                title='Test video',
                url=url,
                domain='bilibili.com',
                duration=120,
                thumbnail='https://img.example.com/video.jpg',
                publish_date=datetime(2024, 1, 1),
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
                is_deleted=False,
            )
        )
        session.commit()


def test_get_video_url_synthesizes_mpd_url_for_split_streams(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_video(engine)

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            return PluginInvokeResponse(
                request_id='video-1',
                ok=True,
                data={
                    'video_url': 'https://cdn.example.com/video.m4s',
                    'audio_url': 'https://cdn.example.com/audio.m4s',
                    'qualities': [{'value': '1080p', 'label': '1080p', 'height': 1080, 'codec': 'avc'}],
                },
            )

    monkeypatch.setattr(
        video_service,
        'get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )

    result = video_service.get_video_url(video_id=1)

    assert result.video_url == 'https://cdn.example.com/video.m4s'
    assert result.audio_url == 'https://cdn.example.com/audio.m4s'
    assert result.mpd_url == '/api/video/mpd?video_id=1'
