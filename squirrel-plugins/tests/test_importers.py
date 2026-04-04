from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PORNHUB_IMPORTER_PATH = (
    REPO_ROOT / 'squirrel-plugins' / 'pornhub' / 'src' / 'squirrel_pornhub' / 'importer.py'
)
JAVDB_IMPORTER_PATH = (
    REPO_ROOT / 'squirrel-plugins' / 'javdb' / 'src' / 'squirrel_javdb' / 'importer.py'
)
YOUTUBE_IMPORTER_PATH = (
    REPO_ROOT / 'squirrel-plugins' / 'youtube' / 'src' / 'squirrel_youtube' / 'importer.py'
)


@dataclass
class _SubscriptionImportItem:
    url: str
    name: str | None = None
    avatar: str | None = None
    extra_data: dict | None = None


@dataclass
class _SubscriptionImportBatchResult:
    items: list[_SubscriptionImportItem]
    cursor_payload: dict | None = None
    has_more: bool = False
    stop_reason: str | None = None
    total_available: int | None = None


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')


class _FakeTag:
    def __init__(self, attrs: dict[str, str] | None = None, text: str = ''):
        self._attrs = attrs or {}
        self.text = text

    def get(self, key: str, default=None):
        return self._attrs.get(key, default)


class _FakeListItem:
    def __init__(self, selector_map: dict[str, list[_FakeTag]], attrs: dict[str, str] | None = None):
        self.selector_map = selector_map
        self._attrs = attrs or {}

    def select(self, selector: str):
        return list(self.selector_map.get(selector, []))

    def get(self, key: str, default=None):
        return self._attrs.get(key, default)


class _FakeSoup:
    def __init__(self, *, select_one_map: dict[str, object] | None = None, select_map: dict[str, list[object]] | None = None):
        self.select_one_map = select_one_map or {}
        self.select_map = select_map or {}

    def select_one(self, selector: str):
        return self.select_one_map.get(selector)

    def select(self, selector: str):
        return list(self.select_map.get(selector, []))


@contextmanager
def _stub_pornhub_importer_dependencies():
    originals = {name: sys.modules.get(name) for name in ('crawl', 'bs4')}
    response_queue: list[_FakeResponse] = []
    soup_registry: dict[str, _FakeSoup] = {}

    crawl_module = types.ModuleType('crawl')
    crawl_module.SubscriptionImportItem = _SubscriptionImportItem
    crawl_module.SubscriptionImportBatchResult = _SubscriptionImportBatchResult
    crawl_module.SubscriptionImportBatchResult = _SubscriptionImportBatchResult
    crawl_module.filter_cookies_to_query_string = lambda _url: 'cookie=1'
    crawl_module.get_http_headers = lambda _site, headers=None: dict(headers or {})

    def request_without_limit(_method, _url, **_kwargs):
        if not response_queue:
            raise AssertionError('No queued response for request')
        return response_queue.pop(0)

    crawl_module.request_without_limit = request_without_limit

    bs4_module = types.ModuleType('bs4')
    bs4_module.BeautifulSoup = lambda html, _parser: soup_registry[html]

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


def _load_pornhub_importer_module():
    module_name = '_importer_test_pornhub'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, PORNHUB_IMPORTER_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


@contextmanager
def _stub_javdb_importer_dependencies():
    originals = {name: sys.modules.get(name) for name in ('crawl', 'bs4', 'squirrel_javdb', 'squirrel_javdb.html_client')}
    response_queue: list[_FakeResponse] = []
    soup_registry: dict[str, _FakeSoup] = {}

    crawl_module = types.ModuleType('crawl')
    crawl_module.SubscriptionImportItem = _SubscriptionImportItem
    crawl_module.SubscriptionImportBatchResult = _SubscriptionImportBatchResult

    bs4_module = types.ModuleType('bs4')
    bs4_module.BeautifulSoup = lambda html, _parser: soup_registry[html]

    package_module = types.ModuleType('squirrel_javdb')
    package_module.__path__ = [str(JAVDB_IMPORTER_PATH.parent)]

    html_client_module = types.ModuleType('squirrel_javdb.html_client')

    def fetch_javdb_html(_url, **_kwargs):
        if not response_queue:
            raise AssertionError('No queued response for fetch_javdb_html')
        return response_queue.pop(0)

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


def _load_javdb_importer_module():
    module_name = 'squirrel_javdb.importer'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, JAVDB_IMPORTER_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


@contextmanager
def _stub_youtube_importer_dependencies():
    originals = {name: sys.modules.get(name) for name in ('crawl', 'bs4')}
    response_queue: list[_FakeResponse] = []
    soup_registry: dict[str, object] = {}

    crawl_module = types.ModuleType('crawl')
    crawl_module.SubscriptionImportItem = _SubscriptionImportItem
    crawl_module.filter_cookies_to_query_string = lambda _url: 'cookie=1'
    crawl_module.get_http_headers = lambda _site, headers=None: dict(headers or {})

    def request_without_limit(_method, _url, **_kwargs):
        if not response_queue:
            raise AssertionError('No queued response for request_without_limit')
        return response_queue.pop(0)

    crawl_module.request_without_limit = request_without_limit

    bs4_module = types.ModuleType('bs4')
    bs4_module.BeautifulSoup = lambda html, _parser: soup_registry.get(html)

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


def _load_youtube_importer_module():
    module_name = '_importer_test_youtube'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, YOUTUBE_IMPORTER_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


class ImporterTests(unittest.TestCase):
    def test_pornhub_importer_skips_malformed_subscription_items(self):
        with _stub_pornhub_importer_dependencies() as (responses, soups):
            module = _load_pornhub_importer_module()

            responses.extend([
                _FakeResponse('profile'),
                _FakeResponse('subscriptions-page-1'),
                _FakeResponse('subscriptions-page-2', status_code=404),
            ])

            soups['profile'] = _FakeSoup(select_one_map={
                '#profileMenuWrapper .profileData a.username[href^="/users/"]': _FakeTag({'href': '/users/demo'}),
            })
            soups['subscriptions-page-1'] = _FakeSoup(select_map={
                'ul#moreData li': [
                    _FakeListItem({}),
                    _FakeListItem({
                        '.usernameWrap .usernameBadgesWrapper a.usernameLink': [
                            _FakeTag({'href': '/model/valid-creator', 'title': 'Valid Creator'}),
                        ],
                        '.userLink .avatar': [
                            _FakeTag({'src': 'https://cdn.example/avatar.jpg'}),
                        ],
                    }),
                ],
            })
            soups['subscriptions-page-2'] = _FakeSoup(select_map={
                'ul#moreData li': [],
            })

            importer = module.PornhubUserSubscriptionImporter()
            items = importer.get_user_subscriptions()

            self.assertEqual(
                items,
                [
                    _SubscriptionImportItem(
                        url='https://www.pornhub.com/model/valid-creator',
                        name='Valid Creator',
                        avatar='https://cdn.example/avatar.jpg',
                    )
                ],
            )

    def test_youtube_yt_initial_data_parser_skips_malformed_channel_renderer(self):
        with _stub_youtube_importer_dependencies() as (_responses, _soups):
            module = _load_youtube_importer_module()
            importer = module.YoutubeUserSubscriptionImporter()

            yt_data = {
                'contents': {
                    'twoColumnBrowseResultsRenderer': {
                        'tabs': [{
                            'tabRenderer': {
                                'selected': True,
                                'content': {
                                    'sectionListRenderer': {
                                        'contents': [{
                                            'itemSectionRenderer': {
                                                'contents': [{
                                                    'shelfRenderer': {
                                                        'content': {
                                                            'expandedShelfContentsRenderer': {
                                                                'items': [
                                                                    {
                                                                        'channelRenderer': {
                                                                            'channelId': 'UCBROKEN0001',
                                                                            'title': {'simpleText': 'Broken Channel'},
                                                                            'thumbnail': {'thumbnails': [None]},
                                                                        }
                                                                    },
                                                                    {
                                                                        'channelRenderer': {
                                                                            'channelId': 'UCVALID00002',
                                                                            'title': {'simpleText': 'Valid Channel'},
                                                                            'thumbnail': {
                                                                                'thumbnails': [
                                                                                    {'url': 'https://cdn.example/thumb-small.jpg', 'width': 48},
                                                                                    {'url': 'https://cdn.example/thumb-large.jpg', 'width': 88},
                                                                                ]
                                                                            },
                                                                        }
                                                                    },
                                                                ]
                                                            }
                                                        }
                                                    }
                                                }]
                                            }
                                        }]
                                    }
                                }
                            }
                        }]
                    }
                }
            }

            subscriptions = importer._parse_subscriptions_from_yt_data(yt_data)

            self.assertEqual(
                subscriptions,
                [
                    _SubscriptionImportItem(
                        url='https://www.youtube.com/channel/UCVALID00002',
                        name='Valid Channel',
                        avatar='https://cdn.example/thumb-large.jpg',
                    )
                ],
            )

    def test_youtube_regex_fallback_preserves_first_seen_channel_order(self):
        with _stub_youtube_importer_dependencies() as (responses, soups):
            module = _load_youtube_importer_module()
            module.set = lambda _items: ['UCSECOND00002', 'UCFIRST000001']

            responses.append(_FakeResponse(
                '{"channelId":"UCFIRST000001"}'
                '{"channelId":"UCSECOND00002"}'
                '{"channelId":"UCFIRST000001"}'
            ))
            soups[responses[0].text] = _FakeSoup(select_map={})

            importer = module.YoutubeUserSubscriptionImporter()
            subscriptions = importer.get_user_subscriptions()

            self.assertEqual(
                subscriptions,
                [
                    _SubscriptionImportItem(url='https://www.youtube.com/channel/UCFIRST000001'),
                    _SubscriptionImportItem(url='https://www.youtube.com/channel/UCSECOND00002'),
                ],
            )

    def test_javdb_importer_skips_malformed_actor_items(self):
        with _stub_javdb_importer_dependencies() as (responses, soups):
            module = _load_javdb_importer_module()

            responses.extend([
                _FakeResponse('actors-page-1'),
            ])

            soups['actors-page-1'] = _FakeSoup(select_map={
                '.actor-box a:has(img.avatar)': [
                    _FakeListItem({}, attrs={'href': '/actors/bad-item'}),
                    _FakeListItem({
                        'img': [_FakeTag({'src': 'https://cdn.example/actor.jpg'})],
                        'strong': [_FakeTag(text='Valid Actor')],
                    }, attrs={'href': '/actors/valid-actor?sort=desc'}),
                ],
                '.pagination .pagination-next': [_FakeTag({'class': ['disabled']})],
            })

            importer = module.JavdbUserSubscriptionImporter()
            items = importer.get_user_subscriptions()

            self.assertEqual(
                items,
                [
                    _SubscriptionImportItem(
                        url='https://javdb.com/actors/valid-actor',
                        name='Valid Actor',
                        avatar='https://cdn.example/actor.jpg',
                    )
                ],
            )

    def test_javdb_importer_returns_cursor_batch_without_scanning_following_pages(self):
        with _stub_javdb_importer_dependencies() as (_responses, soups):
            module = _load_javdb_importer_module()
            requested_urls = []

            def _fetch_javdb_html(url, **_kwargs):
                requested_urls.append(url)
                page = int(url.rsplit('=', 1)[-1])
                return _FakeResponse(f'actors-page-{page}')

            module.fetch_javdb_html = _fetch_javdb_html

            soups['actors-page-1'] = _FakeSoup(select_map={
                '.actor-box a:has(img.avatar)': [
                    _FakeListItem({
                        'img': [_FakeTag({'src': 'https://cdn.example/actor-1.jpg'})],
                        'strong': [_FakeTag(text='Actor One')],
                    }, attrs={'href': '/actors/actor-one'}),
                ],
                '.pagination .pagination-next': [_FakeTag({'class': []})],
                '.pagination a': [
                    _FakeTag({'href': '/users/collection_actors?page=1'}, text='1'),
                    _FakeTag({'href': '/users/collection_actors?page=2'}, text='2'),
                    _FakeTag({'href': '/users/collection_actors?page=3'}, text='3'),
                ],
            })

            importer = module.JavdbUserSubscriptionImporter()
            batch = importer.get_user_subscriptions_batch()

            self.assertEqual(
                requested_urls,
                [
                    'https://javdb.com/users/collection_actors?page=1',
                ],
            )
            self.assertEqual(
                batch.items,
                [_SubscriptionImportItem(
                    url='https://javdb.com/actors/actor-one',
                    name='Actor One',
                    avatar='https://cdn.example/actor-1.jpg',
                )],
            )
            self.assertTrue(batch.has_more)
            self.assertEqual(batch.cursor_payload, {'page': 2})
            self.assertEqual(batch.stop_reason, 'batch_exhausted')


if __name__ == '__main__':
    unittest.main()
