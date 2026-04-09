from __future__ import annotations

import importlib
import importlib.util
import sys
import types
import unittest
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BILIBILI_SUBSCRIPTION_PATH = (
    REPO_ROOT / 'squirrel-plugins' / 'bilibili' / 'src' / 'squirrel_bilibili' / 'subscription.py'
)
PORNHUB_SUBSCRIPTION_PATH = (
    REPO_ROOT / 'squirrel-plugins' / 'pornhub' / 'src' / 'squirrel_pornhub' / 'subscription.py'
)
JAVDB_SUBSCRIPTION_PATH = (
    REPO_ROOT / 'squirrel-plugins' / 'javdb' / 'src' / 'squirrel_javdb' / 'subscription.py'
)
YOUTUBE_SUBSCRIPTION_PATH = (
    REPO_ROOT / 'squirrel-plugins' / 'youtube' / 'src' / 'squirrel_youtube' / 'subscription.py'
)


@dataclass
class _SubscriptionSyncContext:
    mode: str
    cursor_payload: dict = field(default_factory=dict)
    last_seen_video_url: str | None = None
    limit: int | None = None


@dataclass
class _SubscriptionSyncResult:
    video_urls: list[str]
    latest_video_url: str | None
    cursor_payload: dict
    stop_reason: str
    total_available: int | None
    has_more: bool = False
    head_sample_urls: list[str] | None = None
    anchor_found: bool | None = None
    cursor_invalid: bool | None = None
    cursor_loop_detected: bool | None = None


@dataclass
class _SubscriptionMeta:
    id: str | None
    name: str | None
    avatar: str | None
    url: str


def _resolve_subscription_limit(context):
    if context.mode == 'full':
        return None
    return context.limit or 30


def _append_subscription_video_url(
    video_url,
    *,
    video_urls,
    context,
    latest_video_url,
    limit,
    seen_urls=None,
):
    updated_latest_video_url = latest_video_url or video_url
    if context.mode != 'full' and video_url == context.last_seen_video_url:
        return updated_latest_video_url, 'cursor_hit'
    if seen_urls is not None:
        if video_url in seen_urls:
            return updated_latest_video_url, None
        seen_urls.add(video_url)
    elif video_url in video_urls:
        return updated_latest_video_url, None
    video_urls.append(video_url)
    if limit is not None and len(video_urls) >= limit:
        return updated_latest_video_url, 'limit_reached'
    return updated_latest_video_url, None


def _build_subscription_sync_result(
    *,
    video_urls,
    latest_video_url,
    context,
    stop_reason,
    source_video_count=None,
    cursor_payload=None,
    has_more=False,
    total_available=None,
    head_sample_urls=None,
    anchor_found=None,
    cursor_invalid=None,
    cursor_loop_detected=None,
):
    return _SubscriptionSyncResult(
        video_urls=list(video_urls),
        latest_video_url=latest_video_url,
        cursor_payload=(
            cursor_payload
            if cursor_payload is not None
            else {'latest_video_url': latest_video_url} if latest_video_url else context.cursor_payload
        ),
        stop_reason=stop_reason,
        total_available=total_available,
        has_more=has_more,
        head_sample_urls=list(head_sample_urls) if head_sample_urls is not None else None,
        anchor_found=anchor_found,
        cursor_invalid=cursor_invalid,
        cursor_loop_detected=cursor_loop_detected,
    )


@contextmanager
def _stub_pornhub_subscription_dependencies():
    originals = {
        name: sys.modules.get(name)
        for name in ('crawl', 'bs4')
    }

    response_queue: list[object] = []
    soup_registry: dict[str, object] = {}

    crawl_module = types.ModuleType('crawl')
    crawl_module.SubscriptionMeta = _SubscriptionMeta
    crawl_module.SubscriptionSyncContext = _SubscriptionSyncContext
    crawl_module.SubscriptionSyncResult = _SubscriptionSyncResult
    crawl_module.append_subscription_video_url = _append_subscription_video_url
    crawl_module.build_subscription_sync_result = _build_subscription_sync_result
    crawl_module.filter_cookies_to_query_string = lambda _url: ''
    crawl_module.resolve_subscription_limit = _resolve_subscription_limit

    def request(_method, _url, **_kwargs):
        if not response_queue:
            raise AssertionError('No queued response for request')
        return response_queue.pop(0)

    crawl_module.request = request

    bs4_module = types.ModuleType('bs4')

    def BeautifulSoup(html, _parser):
        return soup_registry[html]

    bs4_module.BeautifulSoup = BeautifulSoup

    try:
        sys.modules['crawl'] = crawl_module
        sys.modules['bs4'] = bs4_module
        yield response_queue, soup_registry
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def _load_pornhub_subscription_module():
    module_name = '_subscription_test_pornhub'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, PORNHUB_SUBSCRIPTION_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


@contextmanager
def _stub_javdb_subscription_dependencies():
    originals = {
        name: sys.modules.get(name)
        for name in ('crawl', 'bs4', 'squirrel_javdb', 'squirrel_javdb.html_client')
    }

    response_queue: list[object] = []
    soup_registry: dict[str, object] = {}

    crawl_module = types.ModuleType('crawl')
    crawl_module.SubscriptionMeta = _SubscriptionMeta
    crawl_module.SubscriptionSyncContext = _SubscriptionSyncContext
    crawl_module.SubscriptionSyncResult = _SubscriptionSyncResult
    crawl_module.append_subscription_video_url = _append_subscription_video_url
    crawl_module.build_subscription_sync_result = _build_subscription_sync_result
    crawl_module.resolve_subscription_limit = _resolve_subscription_limit

    bs4_module = types.ModuleType('bs4')

    def BeautifulSoup(html, _parser):
        return soup_registry[html]

    bs4_module.BeautifulSoup = BeautifulSoup

    package_module = types.ModuleType('squirrel_javdb')
    package_module.__path__ = [str(JAVDB_SUBSCRIPTION_PATH.parent)]

    html_client_module = types.ModuleType('squirrel_javdb.html_client')

    def fetch_javdb_html(_url, **_kwargs):
        if not response_queue:
            raise AssertionError('No queued response for fetch_javdb_html')
        return response_queue.pop(0)

    html_client_module.DEFAULT_JAVDB_TIMEOUT_SECONDS = 30.0
    html_client_module.fetch_javdb_html = fetch_javdb_html

    try:
        sys.modules['crawl'] = crawl_module
        sys.modules['bs4'] = bs4_module
        sys.modules['squirrel_javdb'] = package_module
        sys.modules['squirrel_javdb.html_client'] = html_client_module
        yield response_queue, soup_registry
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def _load_javdb_subscription_module():
    module_name = 'squirrel_javdb.subscription'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, JAVDB_SUBSCRIPTION_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


@contextmanager
def _stub_bilibili_subscription_dependencies():
    originals = {
        name: sys.modules.get(name)
        for name in ('crawl', 'squirrel_bilibili', 'squirrel_bilibili.sign')
    }

    response_queue: list[object] = []

    crawl_module = types.ModuleType('crawl')
    crawl_module.SubscriptionMeta = _SubscriptionMeta
    crawl_module.SubscriptionSyncContext = _SubscriptionSyncContext
    crawl_module.SubscriptionSyncResult = _SubscriptionSyncResult
    crawl_module.append_subscription_video_url = _append_subscription_video_url
    crawl_module.build_subscription_sync_result = _build_subscription_sync_result
    crawl_module.resolve_subscription_limit = _resolve_subscription_limit

    package_module = types.ModuleType('squirrel_bilibili')
    package_module.__path__ = [str(BILIBILI_SUBSCRIPTION_PATH.parent)]

    sign_module = types.ModuleType('squirrel_bilibili.sign')

    class _ResourceType:
        FAVORITE_LIST = 'favorite_list'
        CHANNEL_SERIES = 'channel_series'
        SPACE = 'space'

    class _ChannelSeriesType:
        SERIES = 'series'
        SEASON = 'season'

    sign_module.ResourceType = _ResourceType
    sign_module.ChannelSeriesType = _ChannelSeriesType
    sign_module.build_cookies = lambda _url: {}
    sign_module.parse_subscription_target = lambda _url: types.SimpleNamespace(
        resource_type=_ResourceType.FAVORITE_LIST,
        media_id='fav-1',
        mid=None,
        series_id=None,
        series_type=None,
    )
    sign_module.fetch_fav_folder_info = lambda *args, **kwargs: {}
    sign_module.fetch_series_meta = lambda *args, **kwargs: {}
    sign_module.fetch_user_card = lambda *args, **kwargs: {}
    sign_module.fetch_user_videos = lambda *args, **kwargs: {}
    sign_module.fetch_series_videos = lambda *args, **kwargs: {}

    def fetch_fav_resource_list(*_args, **_kwargs):
        if not response_queue:
            raise AssertionError('No queued response for fetch_fav_resource_list')
        return response_queue.pop(0)

    sign_module.fetch_fav_resource_list = fetch_fav_resource_list

    try:
        sys.modules['crawl'] = crawl_module
        sys.modules['squirrel_bilibili'] = package_module
        sys.modules['squirrel_bilibili.sign'] = sign_module
        yield response_queue
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def _load_bilibili_subscription_module():
    module_name = 'squirrel_bilibili.subscription'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, BILIBILI_SUBSCRIPTION_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


@contextmanager
def _stub_youtube_subscription_dependencies():
    originals = {
        name: sys.modules.get(name)
        for name in (
            'crawl',
            'pytubefix',
            'squirrel_youtube',
            'squirrel_youtube.subscription',
            'squirrel_youtube.ytdlp_support',
        )
    }

    crawl_module = types.ModuleType('crawl')
    crawl_module.SubscriptionMeta = _SubscriptionMeta
    crawl_module.SubscriptionSyncContext = _SubscriptionSyncContext
    crawl_module.SubscriptionSyncResult = _SubscriptionSyncResult
    crawl_module.append_subscription_video_url = _append_subscription_video_url
    crawl_module.build_subscription_sync_result = _build_subscription_sync_result
    crawl_module.resolve_subscription_limit = _resolve_subscription_limit
    crawl_module.apply_ytdlp_rate_limit = lambda site_name, options=None: {
        **dict(options or {}),
        '_rate_limit_site': site_name,
    }
    crawl_module.filter_cookies_to_query_string = lambda _url: 'cookie=1'
    crawl_module.resolve_cookie_file_path = lambda _url: None

    pytubefix_module = types.ModuleType('pytubefix')

    class Channel:
        def __new__(cls, *args, **kwargs):
            raise AssertionError('pytubefix.Channel should not be used')

    class Playlist:
        def __new__(cls, *args, **kwargs):
            raise AssertionError('pytubefix.Playlist should not be used')

    pytubefix_module.Channel = Channel
    pytubefix_module.Playlist = Playlist

    package_module = types.ModuleType('squirrel_youtube')
    package_module.__path__ = [str(YOUTUBE_SUBSCRIPTION_PATH.parent)]  # type: ignore[attr-defined]

    try:
        sys.modules['crawl'] = crawl_module
        sys.modules['pytubefix'] = pytubefix_module
        sys.modules['squirrel_youtube'] = package_module
        yield
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def _load_youtube_subscription_module():
    module_name = 'squirrel_youtube.subscription'
    original_sys_path = list(sys.path)
    try:
        sys.modules.pop(module_name, None)
        sys.modules.pop('squirrel_youtube.ytdlp_support', None)
        sys.path.insert(0, str(YOUTUBE_SUBSCRIPTION_PATH.parents[2] / 'src'))
        return importlib.import_module(module_name)
    finally:
        sys.path[:] = original_sys_path


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')


class _FakeVideoElement:
    def __init__(self, href: str):
        self.href = href

    def __getitem__(self, key: str):
        if key != 'href':
            raise KeyError(key)
        return self.href


class _FakePageLabel:
    def __init__(self, text: str):
        self.text = text


class _FakeNextButton:
    def __init__(self, previous_text: str):
        self._previous = _FakePageLabel(previous_text)

    def find_previous(self):
        return self._previous


class _FakeSoup:
    def __init__(self, selector_map: dict[str, list[object]]):
        self.selector_map = selector_map

    def select(self, selector: str):
        return list(self.selector_map.get(selector, []))


class _FakeYoutubeItem:
    def __init__(self, watch_url: str | None):
        self.watch_url = watch_url


def _build_ytdlp_info(
    *,
    entries: list[dict] | None = None,
    channel_id: str = 'channel-1',
    channel: str = 'Demo Channel',
    title: str | None = None,
    thumbnails: list[dict] | None = None,
    playlist_id: str | None = None,
    playlist_count: int | None = None,
):
    return {
        'entries': list(entries or []),
        'channel_id': channel_id,
        'channel': channel,
        'uploader': channel,
        'title': title or f'{channel} - Videos',
        'thumbnails': list(thumbnails or [{'url': 'https://cdn.example/thumb.jpg'}]),
        'id': playlist_id or channel_id,
        'playlist_count': playlist_count,
        'webpage_url': 'https://www.youtube.com/channel/channel-1',
    }


class SubscriptionSyncTests(unittest.TestCase):
    def test_bilibili_full_sync_returns_continuation_cursor_for_next_page(self):
        with _stub_bilibili_subscription_dependencies() as responses:
            module = _load_bilibili_subscription_module()

            responses.append({
                'medias': [
                    {'bvid': 'BV1-demo-page-1'},
                    {'bvid': 'BV2-demo-page-1'},
                ],
                'has_more': True,
            })

            subscription = module.BilibiliSubscription('https://www.bilibili.com/list/ml123')
            result = subscription.sync_videos(_SubscriptionSyncContext(mode='full'))

            self.assertEqual(
                result.video_urls,
                [
                    'https://www.bilibili.com/video/BV1-demo-page-1',
                    'https://www.bilibili.com/video/BV2-demo-page-1',
                ],
            )
            self.assertEqual(result.latest_video_url, 'https://www.bilibili.com/video/BV1-demo-page-1')
            self.assertEqual(result.cursor_payload, {'page': 2})
            self.assertEqual(result.stop_reason, 'batch_exhausted')
            self.assertTrue(result.has_more)

    def test_bilibili_full_sync_resumes_from_cursor_and_finishes_last_page(self):
        with _stub_bilibili_subscription_dependencies() as responses:
            module = _load_bilibili_subscription_module()

            responses.append({
                'medias': [
                    {'bvid': 'BV3-demo-page-2'},
                ],
                'has_more': False,
            })

            subscription = module.BilibiliSubscription('https://www.bilibili.com/list/ml123')
            result = subscription.sync_videos(
                _SubscriptionSyncContext(mode='full', cursor_payload={'page': 2})
            )

            self.assertEqual(
                result.video_urls,
                ['https://www.bilibili.com/video/BV3-demo-page-2'],
            )
            self.assertEqual(result.latest_video_url, 'https://www.bilibili.com/video/BV3-demo-page-2')
            self.assertEqual(result.stop_reason, 'source_exhausted')
            self.assertFalse(result.has_more)

    def test_javdb_full_sync_returns_continuation_cursor_for_next_page(self):
        with _stub_javdb_subscription_dependencies() as (responses, soups):
            module = _load_javdb_subscription_module()

            responses.append(_FakeResponse('javdb-page-1'))
            soups['javdb-page-1'] = _FakeSoup({
                '.movie-list .item a.box': [
                    _FakeVideoElement('/v/one'),
                    _FakeVideoElement('/v/shared'),
                ],
                'a.pagination-link[rel="next"]': [_FakePageLabel('2')],
            })

            subscription = module.JavdbSubscription('https://javdb.com/actors/demo')
            result = subscription.sync_videos(_SubscriptionSyncContext(mode='full'))

            self.assertEqual(
                result.video_urls,
                [
                    'https://javdb.com/v/one',
                    'https://javdb.com/v/shared',
                ],
            )
            self.assertEqual(result.latest_video_url, 'https://javdb.com/v/one')
            self.assertEqual(
                result.cursor_payload,
                {
                    'page': 2,
                    'count_offset': 2,
                    'previous_page_urls': [
                        'https://javdb.com/v/one',
                        'https://javdb.com/v/shared',
                    ],
                },
            )
            self.assertEqual(result.stop_reason, 'batch_exhausted')
            self.assertTrue(result.has_more)

    def test_javdb_full_sync_resumes_from_cursor_and_finishes_on_last_page(self):
        with _stub_javdb_subscription_dependencies() as (responses, soups):
            module = _load_javdb_subscription_module()

            responses.append(_FakeResponse('javdb-page-2'))
            soups['javdb-page-2'] = _FakeSoup({
                '.movie-list .item a.box': [
                    _FakeVideoElement('/v/shared'),
                    _FakeVideoElement('/v/two'),
                ],
                'a.pagination-link[rel="next"]': [],
            })

            subscription = module.JavdbSubscription('https://javdb.com/actors/demo')
            result = subscription.sync_videos(
                _SubscriptionSyncContext(
                    mode='full',
                    cursor_payload={
                        'page': 2,
                        'count_offset': 2,
                        'previous_page_urls': [
                            'https://javdb.com/v/one',
                            'https://javdb.com/v/shared',
                        ],
                    },
                )
            )

            self.assertEqual(
                result.video_urls,
                [
                    'https://javdb.com/v/shared',
                    'https://javdb.com/v/two',
                ],
            )
            self.assertEqual(result.latest_video_url, 'https://javdb.com/v/shared')
            self.assertEqual(result.stop_reason, 'source_exhausted')
            self.assertFalse(result.has_more)
            self.assertEqual(result.total_available, 3)

    def test_javdb_get_subscribe_info_allows_missing_avatar(self):
        with _stub_javdb_subscription_dependencies() as (responses, soups):
            module = _load_javdb_subscription_module()

            responses.append(_FakeResponse('javdb-actor-page'))
            soups['javdb-actor-page'] = _FakeSoup({
                '.actor-section-name': [_FakePageLabel('Demo Actor, Alias')],
                '.avatar': [],
            })

            subscription = module.JavdbSubscription('https://javdb.com/actors/demo')
            info = subscription.get_subscribe_info()

            self.assertEqual(
                info,
                _SubscriptionMeta(
                    'demo',
                    'Demo Actor',
                    None,
                    'https://javdb.com/actors/demo',
                ),
            )

    def test_pornhub_full_sync_returns_continuation_cursor_for_next_page(self):
        with _stub_pornhub_subscription_dependencies() as (responses, soups):
            module = _load_pornhub_subscription_module()

            responses.append(_FakeResponse('page-1'))
            soups['page-1'] = _FakeSoup({
                '#channelsProfile .videos a.videoPreviewBg': [_FakeVideoElement('/view_video.php?viewkey=one')],
                '#profileContent .videos:not(#privateVideosSection) a.videoPreviewBg': [],
                '#pornstarsVideoSection .videoPreviewBg': [],
                '.page_next': [_FakeNextButton('2')],
            })

            subscription = module.PornhubSubscription('https://www.pornhub.com/channels/demo')
            result = subscription.sync_videos(_SubscriptionSyncContext(mode='full'))

            self.assertEqual(result.video_urls, ['https://www.pornhub.com/view_video.php?viewkey=one'])
            self.assertEqual(result.latest_video_url, 'https://www.pornhub.com/view_video.php?viewkey=one')
            self.assertEqual(
                result.cursor_payload,
                {
                    'page': 2,
                    'count_offset': 1,
                    'previous_page_urls': ['https://www.pornhub.com/view_video.php?viewkey=one'],
                },
            )
            self.assertEqual(result.stop_reason, 'batch_exhausted')
            self.assertTrue(result.has_more)

    def test_pornhub_full_sync_resumes_from_cursor_and_finishes_on_last_page(self):
        with _stub_pornhub_subscription_dependencies() as (responses, soups):
            module = _load_pornhub_subscription_module()

            responses.append(_FakeResponse('page-2'))
            soups['page-2'] = _FakeSoup({
                '#channelsProfile .videos a.videoPreviewBg': [_FakeVideoElement('/view_video.php?viewkey=two')],
                '#profileContent .videos:not(#privateVideosSection) a.videoPreviewBg': [],
                '#pornstarsVideoSection .videoPreviewBg': [],
                '.page_next': [],
            })

            subscription = module.PornhubSubscription('https://www.pornhub.com/channels/demo')
            result = subscription.sync_videos(
                _SubscriptionSyncContext(
                    mode='full',
                    cursor_payload={
                        'page': 2,
                        'count_offset': 1,
                        'previous_page_urls': ['https://www.pornhub.com/view_video.php?viewkey=one'],
                    },
                )
            )

            self.assertEqual(result.video_urls, ['https://www.pornhub.com/view_video.php?viewkey=two'])
            self.assertEqual(result.latest_video_url, 'https://www.pornhub.com/view_video.php?viewkey=two')
            self.assertEqual(result.stop_reason, 'source_exhausted')
            self.assertFalse(result.has_more)
            self.assertEqual(result.total_available, 2)

    def test_pornhub_full_sync_deduplicates_video_urls_across_sections(self):
        with _stub_pornhub_subscription_dependencies() as (responses, soups):
            module = _load_pornhub_subscription_module()

            responses.append(_FakeResponse('pornhub-page'))
            soups['pornhub-page'] = _FakeSoup({
                '#channelsProfile .videos a.videoPreviewBg': [
                    _FakeVideoElement('/view_video.php?viewkey=one'),
                    _FakeVideoElement('/view_video.php?viewkey=shared'),
                ],
                '#profileContent .videos:not(#privateVideosSection) a.videoPreviewBg': [
                    _FakeVideoElement('/view_video.php?viewkey=shared'),
                    _FakeVideoElement('/view_video.php?viewkey=two'),
                ],
                '#pornstarsVideoSection .videoPreviewBg': [],
                '.page_next': [],
            })

            subscription = module.PornhubSubscription('https://www.pornhub.com/channels/demo')
            result = subscription.sync_videos(_SubscriptionSyncContext(mode='full'))

            self.assertEqual(
                result.video_urls,
                [
                    'https://www.pornhub.com/view_video.php?viewkey=one',
                    'https://www.pornhub.com/view_video.php?viewkey=shared',
                    'https://www.pornhub.com/view_video.php?viewkey=two',
                ],
            )
            self.assertEqual(result.latest_video_url, 'https://www.pornhub.com/view_video.php?viewkey=one')
            self.assertEqual(result.stop_reason, 'source_exhausted')
            self.assertEqual(result.total_available, 3)

    def test_youtube_channel_sync_deduplicates_overlapping_video_and_short_urls(self):
        with _stub_youtube_subscription_dependencies():
            module = _load_youtube_subscription_module()
            calls = []

            module.youtube_ytdlp_support.apply_youtube_player_strategy = (
                lambda url, opts: opts.setdefault('_auth_urls', []).append(url)
            )

            def fake_extract(url, opts, *, process=False):
                calls.append((url, dict(opts), process))
                if url == 'https://www.youtube.com/@demo':
                    return _build_ytdlp_info(entries=[], playlist_count=3)
                if url.endswith('/videos'):
                    return _build_ytdlp_info(entries=[
                        {'url': 'https://www.youtube.com/watch?v=video001aaa'},
                        {'url': 'https://www.youtube.com/watch?v=shared00001'},
                    ])
                if url.endswith('/shorts'):
                    return _build_ytdlp_info(entries=[
                        {'url': 'https://www.youtube.com/watch?v=shared00001'},
                        {'url': 'https://www.youtube.com/shorts/short000002'},
                    ])
                raise AssertionError(f'Unexpected URL: {url}')

            module.youtube_ytdlp_support.extract_info = fake_extract

            subscription = module.YoutubeSubscription('https://www.youtube.com/@demo')
            result = subscription.sync_videos(_SubscriptionSyncContext(mode='full'))

            self.assertEqual(
                result.video_urls,
                [
                    'https://www.youtube.com/watch?v=video001aaa',
                    'https://www.youtube.com/watch?v=shared00001',
                    'https://www.youtube.com/shorts/short000002',
                ],
            )
            self.assertEqual(result.latest_video_url, 'https://www.youtube.com/watch?v=video001aaa')
            self.assertEqual(result.stop_reason, 'source_exhausted')
            self.assertEqual(result.total_available, 3)
            self.assertEqual(
                [url for url, _opts, _process in calls],
                [
                    'https://www.youtube.com/@demo/videos',
                    'https://www.youtube.com/@demo/shorts',
                    'https://www.youtube.com/@demo',
                ],
            )
            for url, opts, process in calls:
                self.assertFalse(process)
                self.assertEqual(opts.get('_rate_limit_site'), 'youtube')
                self.assertEqual(opts.get('_auth_urls'), [url])
                self.assertEqual(opts.get('extract_flat'), 'in_playlist')

    def test_youtube_incremental_sync_stops_at_cursor_before_appending_seen_item(self):
        with _stub_youtube_subscription_dependencies():
            module = _load_youtube_subscription_module()
            module.youtube_ytdlp_support.apply_youtube_player_strategy = lambda _url, _opts: None
            module.youtube_ytdlp_support.extract_info = (
                lambda url, _opts, *, process=False: _build_ytdlp_info(entries=[
                    {'url': 'https://www.youtube.com/watch?v=new00000001'},
                    {'url': 'https://www.youtube.com/watch?v=seen0000002'},
                    {'url': 'https://www.youtube.com/watch?v=old00000003'},
                ]) if url.endswith('/videos') else _build_ytdlp_info(entries=[])
            )

            subscription = module.YoutubeSubscription('https://www.youtube.com/@demo')
            result = subscription.sync_videos(
                _SubscriptionSyncContext(
                    mode='incremental',
                    last_seen_video_url='https://www.youtube.com/watch?v=seen0000002',
                )
            )

            self.assertEqual(result.video_urls, ['https://www.youtube.com/watch?v=new00000001'])
            self.assertEqual(result.latest_video_url, 'https://www.youtube.com/watch?v=new00000001')
            self.assertEqual(result.stop_reason, 'cursor_hit')
            self.assertEqual(
                result.head_sample_urls,
                [
                    'https://www.youtube.com/watch?v=new00000001',
                    'https://www.youtube.com/watch?v=seen0000002',
                ],
            )
            self.assertIs(result.anchor_found, True)

    def test_youtube_full_sync_returns_continuation_cursor_when_batch_limit_is_hit(self):
        with _stub_youtube_subscription_dependencies():
            module = _load_youtube_subscription_module()
            module.FULL_SYNC_BATCH_SIZE = 2
            calls = []
            module.youtube_ytdlp_support.apply_youtube_player_strategy = lambda _url, _opts: None

            def fake_extract(url, opts, *, process=False):
                calls.append((url, dict(opts), process))
                if url == 'https://www.youtube.com/@demo':
                    return _build_ytdlp_info(entries=[], playlist_count=4)
                if url.endswith('/videos'):
                    entries = [
                        {'url': 'https://www.youtube.com/watch?v=video0000001'},
                        {'url': 'https://www.youtube.com/watch?v=video0000002'},
                        {'url': 'https://www.youtube.com/watch?v=video0000003'},
                    ]
                    start = max(0, int(opts.get('playliststart', 1)) - 1)
                    end = int(opts.get('playlistend', len(entries)))
                    return _build_ytdlp_info(entries=entries[start:end])
                if url.endswith('/shorts'):
                    return _build_ytdlp_info(entries=[
                        {'url': 'https://www.youtube.com/watch?v=shared000001'},
                    ])
                raise AssertionError(f'Unexpected URL: {url}')

            module.youtube_ytdlp_support.extract_info = fake_extract

            subscription = module.YoutubeSubscription('https://www.youtube.com/@demo')
            result = subscription.sync_videos(_SubscriptionSyncContext(mode='full'))

            self.assertEqual(
                result.video_urls,
                [
                    'https://www.youtube.com/watch?v=video0000001',
                    'https://www.youtube.com/watch?v=video0000002',
                ],
            )
            self.assertEqual(result.latest_video_url, 'https://www.youtube.com/watch?v=video0000001')
            self.assertEqual(result.cursor_payload, {'source': 'videos', 'offset': 2})
            self.assertEqual(result.stop_reason, 'batch_exhausted')
            self.assertTrue(result.has_more)
            self.assertEqual(result.total_available, 4)
            self.assertEqual(calls[0][1].get('playlistend'), 3)

    def test_youtube_full_sync_resumes_from_offset_cursor(self):
        with _stub_youtube_subscription_dependencies():
            module = _load_youtube_subscription_module()
            module.FULL_SYNC_BATCH_SIZE = 2
            calls = []
            module.youtube_ytdlp_support.apply_youtube_player_strategy = lambda _url, _opts: None

            def fake_extract(url, opts, *, process=False):
                calls.append((url, dict(opts), process))
                if url == 'https://www.youtube.com/@demo':
                    return _build_ytdlp_info(entries=[], playlist_count=4)
                if url.endswith('/videos'):
                    entries = [
                        {'url': 'https://www.youtube.com/watch?v=video0000001'},
                        {'url': 'https://www.youtube.com/watch?v=video0000002'},
                        {'url': 'https://www.youtube.com/watch?v=video0000003'},
                    ]
                    start = max(0, int(opts.get('playliststart', 1)) - 1)
                    end = int(opts.get('playlistend', len(entries)))
                    return _build_ytdlp_info(entries=entries[start:end])
                if url.endswith('/shorts'):
                    return _build_ytdlp_info(entries=[
                        {'url': 'https://www.youtube.com/watch?v=shared000001'},
                    ])
                raise AssertionError(f'Unexpected URL: {url}')

            module.youtube_ytdlp_support.extract_info = fake_extract

            subscription = module.YoutubeSubscription('https://www.youtube.com/@demo')
            result = subscription.sync_videos(
                _SubscriptionSyncContext(
                    mode='full',
                    cursor_payload={'source': 'videos', 'offset': 2},
                )
            )

            self.assertEqual(
                result.video_urls,
                [
                    'https://www.youtube.com/watch?v=video0000003',
                    'https://www.youtube.com/watch?v=shared000001',
                ],
            )
            self.assertEqual(result.latest_video_url, 'https://www.youtube.com/watch?v=video0000003')
            self.assertEqual(result.stop_reason, 'source_exhausted')
            self.assertFalse(result.has_more)
            self.assertEqual(result.total_available, 4)
            self.assertEqual(calls[0][1].get('playliststart'), 3)

    def test_youtube_get_subscribe_info_uses_ytdlp_channel_metadata(self):
        with _stub_youtube_subscription_dependencies():
            module = _load_youtube_subscription_module()
            module.youtube_ytdlp_support.apply_youtube_player_strategy = lambda _url, _opts: None
            module.youtube_ytdlp_support.extract_info = (
                lambda _url, _opts, *, process=False: _build_ytdlp_info(
                    entries=[],
                    channel_id='UCdemo000001',
                    channel='Demo Channel',
                    thumbnails=[{'url': 'https://cdn.example/avatar.jpg'}],
                )
            )

            subscription = module.YoutubeSubscription('https://www.youtube.com/@demo')
            info = subscription.get_subscribe_info()

            self.assertEqual(
                info,
                _SubscriptionMeta(
                    'UCdemo000001',
                    'Demo Channel',
                    'https://cdn.example/avatar.jpg',
                    'https://www.youtube.com/channel/UCdemo000001',
                ),
            )


if __name__ == '__main__':
    unittest.main()
