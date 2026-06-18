from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
YOUPORN_IMPORTER_PATH = REPO_ROOT / 'squirrel-site-runtimes' / 'youporn' / 'src' / 'squirrel_youporn' / 'importer.py'


@dataclass
class _SubscriptionImportItem:
    url: str
    name: str | None = None
    avatar: str | None = None
    extra_data: dict | None = None


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
    def __init__(self, selector_map: dict[str, list[_FakeTag]]):
        self.selector_map = selector_map

    def select(self, selector: str):
        return list(self.selector_map.get(selector, []))

    def select_one(self, selector: str):
        values = self.select(selector)
        return values[0] if values else None


class _FakeSoup:
    def __init__(self, *, select_one_map: dict[str, object] | None = None, select_map: dict[str, list[object]] | None = None):
        self.select_one_map = select_one_map or {}
        self.select_map = select_map or {}

    def select_one(self, selector: str):
        return self.select_one_map.get(selector)

    def select(self, selector: str):
        return list(self.select_map.get(selector, []))


@contextmanager
def _stub_youporn_importer_dependencies():
    originals = {name: sys.modules.get(name) for name in ('crawl', 'bs4')}
    response_queue: list[_FakeResponse] = []
    soup_registry: dict[str, _FakeSoup] = {}

    import crawl as real_crawl

    crawl_module = types.ModuleType('crawl')
    crawl_module.__dict__.update(real_crawl.__dict__)
    crawl_module.SubscriptionImportItem = _SubscriptionImportItem
    crawl_module.filter_cookies_to_query_string = lambda _url: 'sid=demo'
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


def _load_youporn_importer_module():
    module_name = '_importer_test_youporn'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, YOUPORN_IMPORTER_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


class YouPornImporterTests(unittest.TestCase):
    def test_youporn_importer_collects_unique_subscriptions_from_user_data_endpoints(self):
        with _stub_youporn_importer_dependencies() as (responses, soups):
            module = _load_youporn_importer_module()

            responses.extend([
                _FakeResponse('home'),
                _FakeResponse(
                    '{"data":{"data":['
                    '{"name":"Ghomestory","url":"/amateur/ghomestory/","thumbnail":"https://cdn.example/ghomestory.jpg"},'
                    '{"name":"HotCumChallenge","url":"/amateur/hotcumchallenge/","thumbnail":"https://cdn.example/hotcumchallenge.jpg"}'
                    '],"count":2,"pagination":{"nextPage":"/user/373387121/pornstars-data/?page=2"},"success":true}}'
                ),
                _FakeResponse(
                    '{"data":{"data":['
                    '{"name":"Ghomestory","url":"/amateur/ghomestory/","thumbnail":"https://cdn.example/ghomestory.jpg"}'
                    '],"count":2,"pagination":{"nextPage":""},"success":true}}'
                ),
                _FakeResponse(
                    '{"data":{"data":['
                    '{"name":"Brazzers","url":"/channel/brazzers/","thumbnail":"https://cdn.example/brazzers.jpg"}'
                    '],"count":1,"pagination":{"nextPage":""},"success":true}}'
                ),
            ])

            soups['home'] = _FakeSoup(select_one_map={
                'a[href*="/user/"]': _FakeTag({'href': '/user/373387121/?tab=pornstars&filter=recent'}),
            })

            items = module.YouPornUserSubscriptionImporter().get_user_subscriptions()

            self.assertEqual(
                items,
                [
                    _SubscriptionImportItem(
                        url='https://www.youporn.com/amateur/ghomestory/',
                        name='Ghomestory',
                        avatar='https://cdn.example/ghomestory.jpg',
                    ),
                    _SubscriptionImportItem(
                        url='https://www.youporn.com/amateur/hotcumchallenge/',
                        name='HotCumChallenge',
                        avatar='https://cdn.example/hotcumchallenge.jpg',
                    ),
                    _SubscriptionImportItem(
                        url='https://www.youporn.com/channel/brazzers/',
                        name='Brazzers',
                        avatar='https://cdn.example/brazzers.jpg',
                    ),
                ],
            )


if __name__ == '__main__':
    unittest.main()
