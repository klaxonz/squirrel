from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
YOUTUBE_IMPORTER_PATH = (
    REPO_ROOT / 'squirrel-site-runtimes' / 'youtube' / 'src' / 'squirrel_youtube' / 'importer.py'
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
def _stub_youtube_importer_dependencies():
    originals = {name: sys.modules.get(name) for name in ('crawl', 'bs4')}
    response_queue: list[_FakeResponse] = []
    soup_registry: dict[str, object] = {}

    import crawl as real_crawl

    crawl_module = types.ModuleType('crawl')
    crawl_module.__dict__.update(real_crawl.__dict__)
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


if __name__ == '__main__':
    unittest.main()
