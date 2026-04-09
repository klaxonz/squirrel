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


def test_list_videos_reads_current_page_from_user_video_feed(monkeypatch):
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


def test_list_videos_uses_bulk_thumbnail_lookup(monkeypatch):
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

    bulk_calls = []

    monkeypatch.setattr(
        video_service.thumbnail_downloader_service,
        'get_thumbnail_url',
        lambda video_id, remote_url, video_url=None: (_ for _ in ()).throw(AssertionError('should use bulk thumbnail lookup')),
    )
    monkeypatch.setattr(
        video_service.thumbnail_downloader_service,
        'get_thumbnail_url_map',
        lambda items: bulk_calls.append(items) or {video_id: f'bulk:{remote_url}' for video_id, remote_url, _video_url in items},
        raising=False,
    )

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
    assert len(bulk_calls) == 1
    assert bulk_calls[0] == [(111, 'https://img.example.com/111.jpg', 'https://www.youtube.com/watch?v=111')]
    assert videos[0]['thumbnail'] == 'bulk:https://img.example.com/111.jpg'


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


def test_get_video_counts_uses_feed_rows_for_realtime_counts(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Video(
                id=201,
                title='Read video',
                url='https://www.youtube.com/watch?v=201',
                domain='youtube.com',
                duration=100,
                thumbnail='https://img.example.com/201.jpg',
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
                is_deleted=False,
            ),
            Video(
                id=202,
                title='Unread video',
                url='https://www.youtube.com/watch?v=202',
                domain='youtube.com',
                duration=100,
                thumbnail='https://img.example.com/202.jpg',
                publish_date=datetime(2024, 1, 2, 12, 0, 0),
                created_at=datetime(2024, 1, 2, 12, 0, 0),
                updated_at=datetime(2024, 1, 2, 12, 0, 0),
                is_deleted=False,
            ),
            Video(
                id=203,
                title='Preview video',
                url='https://www.youtube.com/watch?v=203',
                domain='youtube.com',
                duration=100,
                thumbnail='https://img.example.com/203.jpg',
                publish_date=datetime(2999, 1, 1, 12, 0, 0),
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                updated_at=datetime(2024, 1, 1, 12, 0, 0),
                is_deleted=False,
            ),
            UserVideoFeed(user_id=7, subscription_id=1, video_id=201, publish_date=datetime(2024, 1, 3, 12, 0, 0), video_created_at=datetime(2024, 1, 3, 12, 0, 0), domain='youtube.com', is_nsfw=False, created_at=datetime(2024, 1, 3, 12, 0, 0), updated_at=datetime(2024, 1, 3, 12, 0, 0)),
            UserVideoFeed(user_id=7, subscription_id=1, video_id=202, publish_date=datetime(2024, 1, 2, 12, 0, 0), video_created_at=datetime(2024, 1, 2, 12, 0, 0), domain='youtube.com', is_nsfw=False, created_at=datetime(2024, 1, 2, 12, 0, 0), updated_at=datetime(2024, 1, 2, 12, 0, 0)),
            UserVideoFeed(user_id=7, subscription_id=1, video_id=203, publish_date=datetime(2999, 1, 1, 12, 0, 0), video_created_at=datetime(2024, 1, 1, 12, 0, 0), domain='youtube.com', is_nsfw=False, created_at=datetime(2024, 1, 1, 12, 0, 0), updated_at=datetime(2024, 1, 1, 12, 0, 0)),
            VideoHistory(
                user_id=7,
                video_id=201,
                start_time=datetime(2024, 1, 3, 12, 10, 0),
                end_time=datetime(2024, 1, 3, 12, 14, 0),
                duration=100,
                watch_duration=90,
                last_position=90,
                created_at=datetime(2024, 1, 3, 12, 14, 0),
                updated_at=datetime(2024, 1, 3, 12, 14, 0),
            ),
        ])
        session.commit()

    counts = video_service.get_video_counts(
        user_id=7,
        query=None,
        subscription_id=None,
        nsfw='all',
        domains=None,
    )

    assert counts == {
        'all': 2,
        'read': 1,
        'unread': 1,
        'preview': 1,
        'liked': 0,
        'later': 0,
    }


def test_get_video_counts_does_not_order_candidate_videos(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    statements = []

    @event.listens_for(engine, 'before_cursor_execute')
    def _capture_sql(conn, cursor, statement, parameters, context, executemany):
        statements.append(' '.join(str(statement).split()))

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Video(
                id=401,
                title='Counted video',
                url='https://www.youtube.com/watch?v=401',
                domain='youtube.com',
                duration=100,
                thumbnail='https://img.example.com/401.jpg',
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
                is_deleted=False,
            ),
            UserVideoFeed(
                user_id=7,
                subscription_id=1,
                video_id=401,
                publish_date=datetime(2024, 1, 3, 12, 0, 0),
                video_created_at=datetime(2024, 1, 3, 12, 0, 0),
                domain='youtube.com',
                is_nsfw=False,
                created_at=datetime(2024, 1, 3, 12, 0, 0),
                updated_at=datetime(2024, 1, 3, 12, 0, 0),
            ),
        ])
        session.commit()

    counts = video_service.get_video_counts(
        user_id=7,
        query=None,
        subscription_id=None,
        nsfw='all',
        domains=None,
    )

    count_query_sql = next(
        statement for statement in statements
        if 'count(*) FILTER' in statement or 'count(*) AS all_count' in statement.lower()
    )

    assert counts['all'] == 1
    assert ' ORDER BY ' not in count_query_sql.upper()


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
