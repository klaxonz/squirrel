from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sys
from types import SimpleNamespace

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crawl import PluginInvokeResponse
from crawl.runtime_errors import PluginRuntimeError, RuntimeErrorCode
from core.exceptions.video_exceptions import VideoUrlExtractionError
from models import Base
from models.creator import Creator
from models.links import SubscriptionVideo, UserSubscription
from models.subscription import Subscription
from models.video import Video
from models.video_clip_marker import VideoClipMarker
from models.video_history import VideoHistory
from models.video_interaction import VideoInteraction
from models.user_video_feed import UserVideoFeed
from models.links import VideoCreator
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


@event.listens_for(Session, 'before_flush')
def _mirror_user_video_feed_into_subscription_video(session, flush_context, instances):
    pending_pairs = {
        (row.subscription_id, row.video_id)
        for row in session.new
        if isinstance(row, UserVideoFeed)
    }

    if not pending_pairs:
        return

    existing_pairs = {
        (row.subscription_id, row.video_id)
        for row in session.new
        if isinstance(row, SubscriptionVideo)
    }

    for pair in pending_pairs:
        if pair in existing_pairs:
            continue
        if session.get(SubscriptionVideo, pair) is not None:
            continue
        session.add(SubscriptionVideo(subscription_id=pair[0], video_id=pair[1]))


def _setup_test_env(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            Video.__table__,
            Subscription.__table__,
            SubscriptionVideo.__table__,
            Creator.__table__,
            VideoCreator.__table__,
            UserSubscription.__table__,
            VideoHistory.__table__,
            VideoClipMarker.__table__,
            VideoInteraction.__table__,
            UserVideoFeed.__table__,
        ],
    )
    monkeypatch.setattr(video_service, 'get_session', lambda: _managed_session(engine))
    monkeypatch.setattr(video_service.redis_client, 'get', lambda key: None)
    monkeypatch.setattr(video_service.redis_client, 'setex', lambda key, ttl, value: None)
    monkeypatch.setattr(
        video_service.user_config_service,
        'get_config',
        lambda user_id: {'showNsfw': False},
    )
    monkeypatch.setattr(
        video_service.thumbnail_downloader_service,
        'get_thumbnail_url',
        lambda video_id, remote_url, video_url=None: remote_url,
    )
    monkeypatch.setattr(
        video_service.thumbnail_downloader_service,
        'get_thumbnail_url_map',
        lambda items: {video_id: remote_url for video_id, remote_url, _video_url in items},
        raising=False,
    )
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


def test_save_remote_video_creates_local_video(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    video = video_service.save_remote_video({
        'site': 'youtube',
        'url': 'https://www.youtube.com/watch?v=remote-demo',
        'title': 'Remote Demo',
        'thumbnail': 'https://img.example.com/remote.jpg',
        'duration': 240,
        'publish_date': '2024-05-01T12:30:00Z',
        'description': 'Saved from remote search',
        'subscriptions': [{'name': 'Remote Channel', 'url': 'https://www.youtube.com/@remote'}],
        'actors': [{'name': 'Remote Actor'}],
    })

    assert video.id is not None
    assert video.title == 'Remote Demo'
    assert video.url == 'https://www.youtube.com/watch?v=remote-demo'
    assert video.domain == 'youtube.com'
    assert video.thumbnail == 'https://img.example.com/remote.jpg'
    assert video.duration == 240
    assert video.description == 'Saved from remote search'
    assert video.extra_data['source'] == 'remote'
    assert video.extra_data['site'] == 'youtube'
    assert video.extra_data['subscriptions'][0]['name'] == 'Remote Channel'


def test_get_video_returns_remote_profiles_from_saved_video_metadata(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    saved_video = video_service.save_remote_video({
        'site': 'youtube',
        'url': 'https://www.youtube.com/watch?v=remote-profile',
        'title': 'Remote Profile Demo',
        'thumbnail': 'https://img.example.com/remote-profile.jpg',
        'publish_date': '2024-05-01T12:30:00Z',
        'subscriptions': [{
            'id': 'UCremote',
            'type': 'CHANNEL',
            'name': 'Remote Channel',
            'url': 'https://www.youtube.com/@remote',
            'avatar': 'https://img.example.com/channel.jpg',
            'is_nsfw': False,
        }],
        'actors': [{
            'id': 'actor-1',
            'type': 'ACTOR',
            'name': 'Remote Actor',
            'url': 'https://example.com/actor',
            'avatar': 'https://img.example.com/actor.jpg',
        }],
    })

    video = video_service.get_video(user_id=7, video_id=saved_video.id)

    assert video['subscriptions'] == [{
        'id': 'UCremote',
        'name': 'Remote Channel',
        'url': 'https://www.youtube.com/@remote',
        'type': 'CHANNEL',
        'avatar': 'https://img.example.com/channel.jpg',
        'is_nsfw': False,
    }]
    assert video['actors'] == [{
        'id': 'actor-1',
        'name': 'Remote Actor',
        'url': 'https://example.com/actor',
        'type': 'ACTOR',
        'avatar': 'https://img.example.com/actor.jpg',
        'is_nsfw': None,
    }]


def test_save_remote_video_reuses_existing_url(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_video(engine, video_id=42, url='https://www.youtube.com/watch?v=existing')

    video = video_service.save_remote_video({
        'site': 'youtube',
        'url': 'https://www.youtube.com/watch?v=existing',
        'title': 'New Remote Title',
    })

    assert video.id == 42
    assert video.title == 'Test video'


def test_get_video_url_reads_playback_from_plugin_gateway(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_video(engine)

    calls = []

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            calls.append({
                'capability': capability,
                'payload': payload,
                'site_name': site_name,
                'domain': domain,
                'timeout_ms': timeout_ms,
            })
            return PluginInvokeResponse(
                request_id='video-1',
                ok=True,
                data={
                    'video_url': 'https://cdn.example.com/video.m4s',
                    'audio_url': 'https://cdn.example.com/audio.m4s',
                    'mpd_url': '/api/video/mpd?video_id=1',
                    'qualities': [{'value': '1080p', 'label': '1080p', 'height': 1080, 'codec': 'avc'}],
                },
            )

    monkeypatch.setattr(
        video_service,
        'get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )

    result = video_service.get_video_url(video_id=1)

    assert calls == [{
        'capability': 'resolve_playback',
        'payload': {
            'video_id': 1,
            'url': 'https://www.bilibili.com/video/BV1xx411c7mD',
            'domain': 'bilibili.com',
            'title': 'Test video',
        },
        'site_name': 'bilibili',
        'domain': 'bilibili.com',
        'timeout_ms': None,
    }]
    assert result.video_url == 'https://cdn.example.com/video.m4s'
    assert result.audio_url == 'https://cdn.example.com/audio.m4s'
    assert result.mpd_url == '/api/video/mpd?video_id=1'
    assert result.stream_type == 'dash'
    assert result.default_quality_id == '1080p'
    assert result.supports_manual_quality is False
    assert result.qualities[0].value == '1080p'
    assert result.qualities[0].codec == 'avc'


def test_get_video_url_raises_extraction_error_when_plugin_parse_fails(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_video(engine, url='https://www.youtube.com/watch?v=demo')
    monkeypatch.setattr(
        video_service.SiteCatalog,
        'find_site_by_domain',
        lambda domain: ('youtube', {'metadata': {}}),
    )

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            return PluginInvokeResponse(
                request_id='video-1',
                ok=False,
                error=PluginRuntimeError(
                    code=RuntimeErrorCode.PARSE_ERROR,
                    message='无法获取 YouTube 视频播放信息: https://www.youtube.com/watch?v=demo',
                    retryable=False,
                    details={'url': 'https://www.youtube.com/watch?v=demo'},
                ),
            )

    monkeypatch.setattr(
        video_service,
        'get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )

    try:
        video_service.get_video_url(video_id=1)
        assert False, 'expected VideoUrlExtractionError'
    except VideoUrlExtractionError as exc:
        assert '无法获取 YouTube 视频播放信息' in str(exc)


def test_get_video_url_returns_direct_links_for_desktop_client(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_video(engine)

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            assert payload['client_type'] == 'desktop'
            assert payload['direct_playback'] is True
            return PluginInvokeResponse(
                request_id='video-1',
                ok=True,
                data={
                    'video_url': '/api/video/proxy?domain=bilibili.com&url=https%3A%2F%2Fcdn.example.com%2Fvideo.m4s',
                    'audio_url': '/api/video/proxy?domain=bilibili.com&url=https%3A%2F%2Fcdn.example.com%2Faudio.m4s',
                    'mpd_url': '/api/video/mpd?video_id=1',
                },
            )

    monkeypatch.setattr(
        video_service,
        'get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )

    result = video_service.get_video_url(video_id=1, client_type='desktop')

    assert result.video_url == 'https://cdn.example.com/video.m4s'
    assert result.audio_url == 'https://cdn.example.com/audio.m4s'
    assert result.mpd_url == '/api/video/mpd?video_id=1&direct=1'
    assert result.stream_type == 'dash'


def test_get_video_url_uses_client_scoped_cache_keys(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_video(engine)
    monkeypatch.setattr(
        video_service.SiteCatalog,
        'find_site_by_domain',
        lambda domain: ('bilibili', {'metadata': {'player_url_cache': True}}),
    )

    observed_get_keys = []
    observed_set_keys = []

    monkeypatch.setattr(video_service.redis_client, 'get', lambda key: observed_get_keys.append(key) or None)
    monkeypatch.setattr(
        video_service.redis_client,
        'setex',
        lambda key, ttl, value: observed_set_keys.append((key, ttl)),
    )

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            return PluginInvokeResponse(
                request_id='video-1',
                ok=True,
                data={
                    'video_url': '/api/video/proxy?domain=bilibili.com&url=https%3A%2F%2Fcdn.example.com%2Fvideo.m4s',
                    'audio_url': '/api/video/proxy?domain=bilibili.com&url=https%3A%2F%2Fcdn.example.com%2Faudio.m4s',
                    'mpd_url': '/api/video/mpd?video_id=1',
                },
            )

    monkeypatch.setattr(
        video_service,
        'get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )

    video_service.get_video_url(video_id=1, client_type='desktop')
    video_service.get_video_url(video_id=1)

    assert 'video_url:bilibili:1:desktop:direct:auth:default' in observed_get_keys
    assert 'video_url:bilibili:1:default:auth:default' in observed_get_keys
    assert ('video_url:bilibili:1:desktop:direct:auth:default', video_service.VIDEO_URL_CACHE_TTL) in observed_set_keys
    assert ('video_url:bilibili:1:default:auth:default', video_service.VIDEO_URL_CACHE_TTL) in observed_set_keys


def test_get_video_url_uses_youtube_auth_scoped_cache_keys(monkeypatch, tmp_path):
    engine = _setup_test_env(monkeypatch)
    _seed_video(engine, url='https://www.youtube.com/watch?v=demo')
    monkeypatch.setattr(
        video_service.SiteCatalog,
        'find_site_by_domain',
        lambda domain: ('youtube', {'metadata': {'player_url_cache': True}}),
    )
    monkeypatch.setattr(
        video_service,
        'get_site_cookies_file_path',
        lambda site_name: tmp_path / f'{site_name}.txt',
    )
    (tmp_path / 'youtube.txt').write_text('cookie-state-a', encoding='utf-8')
    monkeypatch.setitem(
        sys.modules,
        'services.youtube_oauth_service',
        SimpleNamespace(get_oauth_cache_scope=lambda: 'oauth:state-a'),
    )

    observed_get_keys = []
    observed_set_keys = []

    monkeypatch.setattr(video_service.redis_client, 'get', lambda key: observed_get_keys.append(key) or None)
    monkeypatch.setattr(
        video_service.redis_client,
        'setex',
        lambda key, ttl, value: observed_set_keys.append((key, ttl)),
    )

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            return PluginInvokeResponse(
                request_id='video-1',
                ok=True,
                data={
                    'video_url': 'https://cdn.example.com/video.m4s',
                    'audio_url': 'https://cdn.example.com/audio.m4s',
                    'mpd_url': '/api/video/mpd?video_id=1',
                },
            )

    monkeypatch.setattr(
        video_service,
        'get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )

    video_service.get_video_url(video_id=1)

    assert observed_get_keys == ['video_url:youtube:1:default:oauth:state-a:cookie:ef1b831d0e796e79']
    assert observed_set_keys == [('video_url:youtube:1:default:oauth:state-a:cookie:ef1b831d0e796e79', video_service.VIDEO_URL_CACHE_TTL)]


def test_get_video_url_unwraps_cookie_bound_desktop_sites_to_direct_links(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    _seed_video(engine, url='https://www.youporn.com/watch/123456/demo-video/')
    monkeypatch.setattr(
        video_service.SiteCatalog,
        'find_site_by_domain',
        lambda domain: ('youporn', {'metadata': {'requires_cookies': True}}),
    )

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            assert payload['client_type'] == 'desktop'
            assert payload['direct_playback'] is True
            return PluginInvokeResponse(
                request_id='video-1',
                ok=True,
                data={
                    'video_url': '/api/video/proxy?domain=youporn.com&url=https%3A%2F%2Fcdn.example.com%2Fmaster.m3u8',
                    'audio_url': None,
                    'mpd_url': '/api/video/mpd?video_id=1',
                },
            )

    monkeypatch.setattr(
        video_service,
        'get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )

    result = video_service.get_video_url(video_id=1, client_type='desktop')

    assert result.video_url == 'https://cdn.example.com/master.m3u8'
    assert result.audio_url is None
    assert result.mpd_url == '/api/video/mpd?video_id=1&direct=1'
    assert result.stream_type == 'dash'


def test_list_videos_reads_current_page_from_user_video_feed(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    statements = []

    @event.listens_for(engine, 'before_cursor_execute')
    def _capture_sql(conn, cursor, statement, parameters, context, executemany):
        statements.append(' '.join(str(statement).split()))

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Subscription(
                id=1,
                type='CHANNEL',
                name='Feed A',
                url='https://www.youtube.com/channel/A',
                avatar='https://img.example.com/a.jpg',
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            Subscription(
                id=2,
                type='CHANNEL',
                name='Feed B',
                url='https://www.youtube.com/channel/B',
                avatar='https://img.example.com/b.jpg',
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            UserSubscription(id=1, user_id=7, subscription_id=1, is_deleted=False, is_nsfw=False, created_at=datetime(2024, 1, 1), updated_at=datetime(2024, 1, 1)),
            UserSubscription(id=2, user_id=7, subscription_id=2, is_deleted=False, is_nsfw=False, created_at=datetime(2024, 1, 1), updated_at=datetime(2024, 1, 1)),
            Video(
                id=101,
                title='Newest video',
                url='https://www.youtube.com/watch?v=101',
                domain='youtube.com',
                duration=240,
                thumbnail='https://img.example.com/101.jpg',
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
                is_deleted=False,
            ),
            Video(
                id=100,
                title='Older video',
                url='https://www.youtube.com/watch?v=100',
                domain='youtube.com',
                duration=180,
                thumbnail='https://img.example.com/100.jpg',
                publish_date=datetime(2024, 1, 2, 12, 0, 0),
                created_at=datetime(2024, 1, 2, 12, 0, 0),
                updated_at=datetime(2024, 1, 2, 12, 0, 0),
                is_deleted=False,
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=1,
                video_id=101,
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                video_created_at=datetime(2024, 1, 3, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=2,
                video_id=101,
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                video_created_at=datetime(2024, 1, 3, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=1,
                video_id=100,
                publish_date=datetime(2024, 1, 2, 12, 0, 0),
                video_created_at=datetime(2024, 1, 2, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 2, 12, 0, 0),
                updated_at=datetime(2024, 1, 2, 12, 0, 0),
            ),
            VideoHistory(
                user_id=7,
                video_id=101,
                start_time=datetime(2024, 1, 3, 12, 10, 0),
                end_time=datetime(2024, 1, 3, 12, 14, 0),
                duration=240,
                watch_duration=120,
                last_position=91,
                created_at=datetime(2024, 1, 3, 12, 14, 0),
                updated_at=datetime(2024, 1, 3, 12, 14, 0),
            ),
        ])
        session.commit()

    videos, total = video_service.list_videos(
        user_id=7,
        query=None,
        subscription_id=None,
        category='all',
        sort_by='publish_date',
        nsfw='all',
        domains=None,
        page=1,
        page_size=2,
        with_total=True,
    )

    assert total == 2
    assert [video['id'] for video in videos] == [101, 100]
    assert videos[0]['last_position'] == 91
    assert {sub['id'] for sub in videos[0]['subscriptions']} == {1, 2}
    feed_page_statements = [
        statement for statement in statements
        if 'FROM user_video_feed' in statement and ' LIMIT ' in statement
    ]
    assert feed_page_statements
    assert all('GROUP BY' not in statement for statement in feed_page_statements)


def test_list_videos_returns_remote_thumbnail_urls_directly(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Subscription(
                id=1,
                type='CHANNEL',
                name='Feed A',
                url='https://www.youtube.com/channel/A',
                avatar='https://img.example.com/a.jpg',
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            UserSubscription(
                id=1,
                user_id=7,
                subscription_id=1,
                is_deleted=False,
                is_nsfw=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            Video(
                id=111,
                title='Bulk thumbnail video',
                url='https://www.youtube.com/watch?v=111',
                domain='youtube.com',
                duration=180,
                thumbnail='https://img.example.com/111.jpg',
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
                is_deleted=False,
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=1,
                video_id=111,
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                video_created_at=datetime(2024, 1, 3, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
            ),
        ])
        session.commit()

    videos, total = video_service.list_videos(
        user_id=7,
        query=None,
        subscription_id=None,
        category='all',
        sort_by='publish_date',
        nsfw='all',
        domains=None,
        page=1,
        page_size=10,
        with_total=False,
    )

    assert total is None
    assert videos[0]['thumbnail'] == 'https://img.example.com/111.jpg'


def test_list_videos_filters_domains_from_user_video_feed(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    statements = []

    @event.listens_for(engine, 'before_cursor_execute')
    def _capture_sql(conn, cursor, statement, parameters, context, executemany):
        statements.append(' '.join(str(statement).split()))

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Subscription(
                id=1,
                type='CHANNEL',
                name='Bilibili Feed',
                url='https://space.bilibili.com/1',
                avatar='https://img.example.com/a.jpg',
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            UserSubscription(
                id=1,
                user_id=7,
                subscription_id=1,
                is_deleted=False,
                is_nsfw=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            Video(
                id=121,
                title='Bilibili video',
                url='https://www.bilibili.com/video/BV121',
                domain='bilibili.com',
                duration=180,
                thumbnail='https://img.example.com/121.jpg',
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
                is_deleted=False,
            ),
            Video(
                id=122,
                title='Youtube video',
                url='https://www.youtube.com/watch?v=122',
                domain='youtube.com',
                duration=180,
                thumbnail='https://img.example.com/122.jpg',
                publish_date=datetime(2024, 1, 4, 12, 0, 0),
                created_at=datetime(2024, 1, 4, 12, 0, 0),
                updated_at=datetime(2024, 1, 4, 12, 0, 0),
                is_deleted=False,
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=1,
                video_id=121,
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                video_created_at=datetime(2024, 1, 3, 12, 0, 0),
                domain='bilibili.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=1,
                video_id=122,
                publish_date=datetime(2024, 1, 4, 12, 0, 0),
                video_created_at=datetime(2024, 1, 4, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 4, 12, 0, 0),
                updated_at=datetime(2024, 1, 4, 12, 0, 0),
            ),
        ])
        session.commit()

    videos, total = video_service.list_videos(
        user_id=7,
        query=None,
        subscription_id=None,
        category='all',
        sort_by='publish_date',
        nsfw='all',
        domains=['bilibili.com', 'b23.tv'],
        page=1,
        page_size=10,
        with_total=False,
    )

    page_statements = [
        statement for statement in statements
        if 'FROM user_video_feed' in statement and ' LIMIT ' in statement
    ]

    assert total is None
    assert [video['id'] for video in videos] == [121]
    assert page_statements
    assert all('EXISTS (SELECT 1 FROM subscription_video' not in statement for statement in page_statements)
    assert any('user_video_feed.domain IN' in statement for statement in page_statements)


def test_list_videos_preserves_unique_pagination_when_feed_has_duplicates(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Subscription(
                id=1,
                type='CHANNEL',
                name='Feed A',
                url='https://www.youtube.com/channel/A',
                avatar='https://img.example.com/a.jpg',
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            Subscription(
                id=2,
                type='CHANNEL',
                name='Feed B',
                url='https://www.youtube.com/channel/B',
                avatar='https://img.example.com/b.jpg',
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            UserSubscription(id=1, user_id=7, subscription_id=1, is_deleted=False, is_nsfw=False, created_at=datetime(2024, 1, 1), updated_at=datetime(2024, 1, 1)),
            UserSubscription(id=2, user_id=7, subscription_id=2, is_deleted=False, is_nsfw=False, created_at=datetime(2024, 1, 1), updated_at=datetime(2024, 1, 1)),
            Video(
                id=103,
                title='Newest duplicate video',
                url='https://www.youtube.com/watch?v=103',
                domain='youtube.com',
                duration=240,
                thumbnail='https://img.example.com/103.jpg',
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
                is_deleted=False,
            ),
            Video(
                id=102,
                title='Second video',
                url='https://www.youtube.com/watch?v=102',
                domain='youtube.com',
                duration=180,
                thumbnail='https://img.example.com/102.jpg',
                publish_date=datetime(2024, 1, 2, 12, 0, 0),
                created_at=datetime(2024, 1, 2, 12, 0, 0),
                updated_at=datetime(2024, 1, 2, 12, 0, 0),
                is_deleted=False,
            ),
            Video(
                id=101,
                title='Third video',
                url='https://www.youtube.com/watch?v=101',
                domain='youtube.com',
                duration=120,
                thumbnail='https://img.example.com/101.jpg',
                publish_date=datetime(2024, 1, 1, 12, 0, 0),
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                updated_at=datetime(2024, 1, 1, 12, 0, 0),
                is_deleted=False,
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=1,
                video_id=103,
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                video_created_at=datetime(2024, 1, 3, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=2,
                video_id=103,
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                video_created_at=datetime(2024, 1, 3, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=1,
                video_id=102,
                publish_date=datetime(2024, 1, 2, 12, 0, 0),
                video_created_at=datetime(2024, 1, 2, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 2, 12, 0, 0),
                updated_at=datetime(2024, 1, 2, 12, 0, 0),
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=1,
                video_id=101,
                publish_date=datetime(2024, 1, 1, 12, 0, 0),
                video_created_at=datetime(2024, 1, 1, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                updated_at=datetime(2024, 1, 1, 12, 0, 0),
            ),
        ])
        session.commit()

    videos, total = video_service.list_videos(
        user_id=7,
        query=None,
        subscription_id=None,
        category='all',
        sort_by='publish_date',
        nsfw='all',
        domains=None,
        page=2,
        page_size=1,
        with_total=False,
    )

    assert total is None
    assert [video['id'] for video in videos] == [102]


def test_list_videos_paginates_liked_results_without_scanning_duplicate_feed_rows(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    duplicate_subscription_count = 205
    statements = []

    @event.listens_for(engine, 'before_cursor_execute')
    def _capture_sql(conn, cursor, statement, parameters, context, executemany):
        normalized = ' '.join(str(statement).split())
        statements.append(normalized)

    with Session(engine, expire_on_commit=False) as session:
        subscriptions = []
        user_subscriptions = []
        feed_rows = []
        interactions = []

        for subscription_id in range(1, duplicate_subscription_count + 1):
            subscriptions.append(
                Subscription(
                    id=subscription_id,
                    type='CHANNEL',
                    name=f'Feed {subscription_id}',
                    url=f'https://www.youtube.com/channel/{subscription_id}',
                    avatar=f'https://img.example.com/{subscription_id}.jpg',
                    description=None,
                    total_videos=0,
                    is_deleted=False,
                    extra_data={},
                    created_at=datetime(2024, 1, 1),
                    updated_at=datetime(2024, 1, 1),
                )
            )
            user_subscriptions.append(
                UserSubscription(
                    id=subscription_id,
                    user_id=7,
                    subscription_id=subscription_id,
                    is_deleted=False,
                    is_nsfw=False,
                    created_at=datetime(2024, 1, 1),
                    updated_at=datetime(2024, 1, 1),
                )
            )
            feed_rows.append(
                UserVideoFeed(
                    user_id=7,
                    subscription_id=subscription_id,
                    video_id=301,
                    publish_date=datetime(2024, 1, 3, 12, 0, 0),
                    video_created_at=datetime(2024, 1, 3, 12, 0, 0),
                    domain='youtube.com',
                    is_nsfw=False,
                    created_at=datetime(2024, 1, 3, 12, 0, 0),
                    updated_at=datetime(2024, 1, 3, 12, 0, 0),
                )
            )

        subscriptions.append(
            Subscription(
                id=duplicate_subscription_count + 1,
                type='CHANNEL',
                name='Feed secondary',
                url='https://www.youtube.com/channel/secondary',
                avatar='https://img.example.com/secondary.jpg',
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            )
        )
        user_subscriptions.append(
            UserSubscription(
                id=duplicate_subscription_count + 1,
                user_id=7,
                subscription_id=duplicate_subscription_count + 1,
                is_deleted=False,
                is_nsfw=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            )
        )
        feed_rows.append(
            UserVideoFeed(
                user_id=7,
                subscription_id=duplicate_subscription_count + 1,
                video_id=302,
                publish_date=datetime(2024, 1, 2, 12, 0, 0),
                video_created_at=datetime(2024, 1, 2, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 2, 12, 0, 0),
                updated_at=datetime(2024, 1, 2, 12, 0, 0),
            )
        )

        session.add_all(subscriptions)
        session.add_all(user_subscriptions)
        session.add_all([
            Video(
                id=301,
                title='Primary liked video',
                url='https://www.youtube.com/watch?v=301',
                domain='youtube.com',
                duration=240,
                thumbnail='https://img.example.com/301.jpg',
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
                is_deleted=False,
            ),
            Video(
                id=302,
                title='Secondary liked video',
                url='https://www.youtube.com/watch?v=302',
                domain='youtube.com',
                duration=180,
                thumbnail='https://img.example.com/302.jpg',
                publish_date=datetime(2024, 1, 2, 12, 0, 0),
                created_at=datetime(2024, 1, 2, 12, 0, 0),
                updated_at=datetime(2024, 1, 2, 12, 0, 0),
                is_deleted=False,
            ),
        ])
        session.add_all(feed_rows)
        session.add_all([
            VideoInteraction(
                user_id=7,
                video_id=301,
                interaction_type=1,
                created_at=datetime(2024, 1, 3, 12, 5, 0),
                updated_at=datetime(2024, 1, 3, 12, 5, 0),
            ),
            VideoInteraction(
                user_id=7,
                video_id=302,
                interaction_type=1,
                created_at=datetime(2024, 1, 2, 12, 5, 0),
                updated_at=datetime(2024, 1, 2, 12, 5, 0),
            ),
        ])
        session.commit()

    videos, total = video_service.list_videos(
        user_id=7,
        query=None,
        subscription_id=None,
        category='liked',
        sort_by='publish_date',
        nsfw='all',
        domains=None,
        page=1,
        page_size=2,
        with_total=False,
    )

    liked_page_scans = [
        statement for statement in statements
        if 'FROM user_video_feed' in statement
        and 'video_interaction' in statement
        and 'GROUP BY' not in statement
        and 'JOIN subscription ON subscription.id = user_video_feed.subscription_id' not in statement
    ]

    assert total is None
    assert [video['id'] for video in videos] == [301, 302]
    assert liked_page_scans == []


def test_list_videos_search_matches_subscription_name(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Subscription(
                id=1,
                type='CHANNEL',
                name='Alpha Feed',
                url='https://www.youtube.com/channel/alpha',
                avatar=None,
                description='Alpha channel',
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            Subscription(
                id=2,
                type='CHANNEL',
                name='Beta Search Match',
                url='https://www.youtube.com/channel/beta',
                avatar=None,
                description='Beta channel',
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            UserSubscription(id=1, user_id=7, subscription_id=1, is_deleted=False, is_nsfw=False, created_at=datetime(2024, 1, 1), updated_at=datetime(2024, 1, 1)),
            UserSubscription(id=2, user_id=7, subscription_id=2, is_deleted=False, is_nsfw=False, created_at=datetime(2024, 1, 1), updated_at=datetime(2024, 1, 1)),
            Video(
                id=501,
                title='First unrelated video',
                url='https://www.youtube.com/watch?v=501',
                domain='youtube.com',
                duration=180,
                thumbnail='https://img.example.com/501.jpg',
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
                is_deleted=False,
            ),
            Video(
                id=502,
                title='Second unrelated video',
                url='https://www.youtube.com/watch?v=502',
                domain='youtube.com',
                duration=180,
                thumbnail='https://img.example.com/502.jpg',
                publish_date=datetime(2024, 1, 2, 12, 0, 0),
                created_at=datetime(2024, 1, 2, 12, 0, 0),
                updated_at=datetime(2024, 1, 2, 12, 0, 0),
                is_deleted=False,
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=1,
                video_id=501,
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                video_created_at=datetime(2024, 1, 3, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=2,
                video_id=502,
                publish_date=datetime(2024, 1, 2, 12, 0, 0),
                video_created_at=datetime(2024, 1, 2, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 2, 12, 0, 0),
                updated_at=datetime(2024, 1, 2, 12, 0, 0),
            ),
        ])
        session.commit()

    videos, total = video_service.list_videos(
        user_id=7,
        query='channel:"Beta Search Match"',
        subscription_id=None,
        category='all',
        sort_by='publish_date',
        nsfw='all',
        domains=None,
        page=1,
        page_size=10,
        with_total=True,
    )

    assert total == 1
    assert [video['id'] for video in videos] == [502]


def test_list_videos_default_search_matches_title_only(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Subscription(
                id=1,
                type='CHANNEL',
                name='Archive Feed',
                url='https://www.youtube.com/channel/archive',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            Subscription(
                id=2,
                type='CHANNEL',
                name='Gamma Subscription',
                url='https://www.youtube.com/channel/gamma',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            UserSubscription(id=1, user_id=7, subscription_id=1, is_deleted=False, is_nsfw=False, created_at=datetime(2024, 1, 1), updated_at=datetime(2024, 1, 1)),
            UserSubscription(id=2, user_id=7, subscription_id=2, is_deleted=False, is_nsfw=False, created_at=datetime(2024, 1, 1), updated_at=datetime(2024, 1, 1)),
            Video(
                id=511,
                title='Gamma title match',
                url='https://www.youtube.com/watch?v=511',
                domain='youtube.com',
                duration=180,
                thumbnail='https://img.example.com/511.jpg',
                publish_date=datetime(2024, 1, 1, 12, 0, 0),
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                updated_at=datetime(2024, 1, 1, 12, 0, 0),
                is_deleted=False,
            ),
            Video(
                id=512,
                title='Fresh unrelated upload',
                url='https://www.youtube.com/watch?v=512',
                domain='youtube.com',
                duration=180,
                thumbnail='https://img.example.com/512.jpg',
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
                is_deleted=False,
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=1,
                video_id=511,
                publish_date=datetime(2024, 1, 1, 12, 0, 0),
                video_created_at=datetime(2024, 1, 1, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                updated_at=datetime(2024, 1, 1, 12, 0, 0),
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=2,
                video_id=512,
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                video_created_at=datetime(2024, 1, 3, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
            ),
        ])
        session.commit()

    videos, total = video_service.list_videos(
        user_id=7,
        query='gamma',
        subscription_id=None,
        category='all',
        sort_by='publish_date',
        nsfw='all',
        domains=None,
        page=1,
        page_size=10,
        with_total=True,
    )

    assert total == 1
    assert [video['id'] for video in videos] == [511]


def test_list_videos_search_no_longer_matches_creator_name(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Subscription(
                id=1,
                type='CHANNEL',
                name='Plain Feed',
                url='https://www.youtube.com/channel/plain',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            UserSubscription(
                id=1,
                user_id=7,
                subscription_id=1,
                is_deleted=False,
                is_nsfw=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            Video(
                id=521,
                title='Plain title',
                url='https://www.youtube.com/watch?v=521',
                domain='youtube.com',
                duration=180,
                thumbnail='https://img.example.com/521.jpg',
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
                is_deleted=False,
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=1,
                video_id=521,
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                video_created_at=datetime(2024, 1, 3, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
            ),
            Creator(
                id=1,
                name='Unique Creator Keyword',
                url='https://example.com/creator/1',
                description=None,
                is_deleted=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            VideoCreator(video_id=521, creator_id=1),
        ])
        session.commit()

    videos, total = video_service.list_videos(
        user_id=7,
        query='creator:"Unique Creator Keyword"',
        subscription_id=None,
        category='all',
        sort_by='publish_date',
        nsfw='all',
        domains=None,
        page=1,
        page_size=10,
        with_total=True,
    )

    assert total == 0
    assert videos == []


def test_list_videos_hides_nsfw_results_when_show_nsfw_disabled(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Subscription(
                id=1,
                type='CHANNEL',
                name='Hidden NSFW feed',
                url='https://www.youtube.com/channel/nsfw',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            UserSubscription(
                id=1,
                user_id=7,
                subscription_id=1,
                is_deleted=False,
                is_nsfw=True,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            Video(
                id=601,
                title='Hidden NSFW video',
                url='https://www.youtube.com/watch?v=601',
                domain='youtube.com',
                duration=180,
                thumbnail='https://img.example.com/601.jpg',
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
                is_deleted=False,
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=1,
                video_id=601,
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                video_created_at=datetime(2024, 1, 3, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=True,
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
            ),
        ])
        session.commit()

    videos, total = video_service.list_videos(
        user_id=7,
        query=None,
        subscription_id=None,
        category='all',
        sort_by='publish_date',
        nsfw='yes',
        domains=None,
        page=1,
        page_size=10,
        with_total=True,
    )

    assert total == 0
    assert videos == []


def test_list_videos_ignores_deleted_user_subscription_feed_rows(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Subscription(
                id=1,
                type='CHANNEL',
                name='Removed feed',
                url='https://www.youtube.com/channel/removed',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            UserSubscription(
                id=1,
                user_id=7,
                subscription_id=1,
                is_deleted=True,
                is_nsfw=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 2),
            ),
            Video(
                id=801,
                title='Removed subscription video',
                url='https://www.youtube.com/watch?v=801',
                domain='youtube.com',
                duration=180,
                thumbnail='https://img.example.com/801.jpg',
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
                is_deleted=False,
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=1,
                video_id=801,
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                video_created_at=datetime(2024, 1, 3, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
            ),
        ])
        session.commit()

    videos, total = video_service.list_videos(
        user_id=7,
        query=None,
        subscription_id=None,
        category='all',
        sort_by='publish_date',
        nsfw='all',
        domains=None,
        page=1,
        page_size=10,
        with_total=True,
    )
    assert total == 0
    assert videos == []


def test_list_videos_subscription_metadata_ignores_deleted_feed_links(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Subscription(
                id=1,
                type='CHANNEL',
                name='Active feed',
                url='https://www.youtube.com/channel/active',
                avatar='https://img.example.com/active.jpg',
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            Subscription(
                id=2,
                type='CHANNEL',
                name='Removed feed',
                url='https://www.youtube.com/channel/removed',
                avatar='https://img.example.com/removed.jpg',
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            UserSubscription(id=1, user_id=7, subscription_id=1, is_deleted=False, is_nsfw=False, created_at=datetime(2024, 1, 1), updated_at=datetime(2024, 1, 1)),
            UserSubscription(id=2, user_id=7, subscription_id=2, is_deleted=True, is_nsfw=False, created_at=datetime(2024, 1, 1), updated_at=datetime(2024, 1, 2)),
            Video(
                id=802,
                title='Shared video',
                url='https://www.youtube.com/watch?v=802',
                domain='youtube.com',
                duration=180,
                thumbnail='https://img.example.com/802.jpg',
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
                is_deleted=False,
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=1,
                video_id=802,
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                video_created_at=datetime(2024, 1, 3, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=2,
                video_id=802,
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                video_created_at=datetime(2024, 1, 3, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
            ),
        ])
        session.commit()

    videos, total = video_service.list_videos(
        user_id=7,
        query=None,
        subscription_id=None,
        category='all',
        sort_by='publish_date',
        nsfw='all',
        domains=None,
        page=1,
        page_size=10,
        with_total=True,
    )

    assert total == 1
    assert [video['id'] for video in videos] == [802]
    assert [subscription['id'] for subscription in videos[0]['subscriptions']] == [1]


def test_get_video_prefers_actual_extract_count_when_subscription_total_is_stale(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Subscription(
                id=1,
                type='CHANNEL',
                name='Deep Channel',
                url='https://www.youtube.com/channel/deep-channel',
                avatar=None,
                description=None,
                total_videos=1,
                is_deleted=False,
                extra_data={},
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            UserSubscription(
                id=1,
                user_id=7,
                subscription_id=1,
                is_deleted=False,
                is_nsfw=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            Video(
                id=701,
                title='Deep Dive',
                url='https://www.youtube.com/watch?v=701',
                domain='youtube.com',
                duration=180,
                thumbnail='https://img.example.com/701.jpg',
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
                is_deleted=False,
            ),
            Video(
                id=702,
                title='Deep Dive 2',
                url='https://www.youtube.com/watch?v=702',
                domain='youtube.com',
                duration=180,
                thumbnail='https://img.example.com/702.jpg',
                publish_date=datetime(2024, 1, 4, 12, 0, 0),
                created_at=datetime(2024, 1, 4, 12, 0, 0),
                updated_at=datetime(2024, 1, 4, 12, 0, 0),
                is_deleted=False,
            ),
            SubscriptionVideo(subscription_id=1, video_id=701),
            SubscriptionVideo(subscription_id=1, video_id=702),
            VideoClipMarker(
                id=1,
                user_id=7,
                video_id=701,
                title='Best part',
                note='Use this in share links',
                preview_image_url='/static/clip-markers/user_7/video_701/marker_1.jpg',
                start_time=42,
                end_time=63,
                created_at=datetime(2024, 1, 3, 12, 30, 0),
                updated_at=datetime(2024, 1, 3, 12, 30, 0),
            ),
        ])
        session.commit()

    video = video_service.get_video(user_id=7, video_id=701)

    assert video is not None
    assert video['subscriptions'][0]['total_extract'] == 2
    assert video['subscriptions'][0]['total_videos'] == 2
    assert len(video['clip_markers']) == 1
    assert video['clip_markers'][0]['title'] == 'Best part'
    assert video['clip_markers'][0]['duration_seconds'] == 21
    assert video['clip_markers'][0]['preview_image_url'].startswith('/static/clip-markers/user_7/video_701/marker_1.jpg')


def test_get_video_gracefully_skips_clip_markers_when_table_is_missing(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            Video.__table__,
            Subscription.__table__,
            SubscriptionVideo.__table__,
            Creator.__table__,
            VideoCreator.__table__,
            UserSubscription.__table__,
            VideoHistory.__table__,
            VideoInteraction.__table__,
            UserVideoFeed.__table__,
        ],
    )
    monkeypatch.setattr(video_service, 'get_session', lambda: _managed_session(engine))
    monkeypatch.setattr(
        video_service.thumbnail_downloader_service,
        'get_thumbnail_url',
        lambda video_id, remote_url, video_url=None: remote_url,
    )

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Subscription(
                id=1,
                name='Fallback Channel',
                url='https://www.youtube.com/@fallback',
                type='CHANNEL',
                avatar='https://img.example.com/channel.jpg',
                total_videos=1,
                is_deleted=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            UserSubscription(
                id=1,
                user_id=7,
                subscription_id=1,
                is_deleted=False,
                is_nsfw=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            ),
            Video(
                id=901,
                title='No marker table',
                url='https://www.youtube.com/watch?v=901',
                domain='youtube.com',
                duration=180,
                thumbnail='https://img.example.com/901.jpg',
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
                is_deleted=False,
            ),
            SubscriptionVideo(subscription_id=1, video_id=901),
        ])
        session.commit()

    video = video_service.get_video(user_id=7, video_id=901)

    assert video is not None
    assert video['id'] == 901
    assert video['clip_markers'] == []
