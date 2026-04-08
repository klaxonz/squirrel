from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
YOUPORN_SUBSCRIPTION_PATH = (
    REPO_ROOT / 'squirrel-plugins' / 'youporn' / 'src' / 'squirrel_youporn' / 'subscription.py'
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


@dataclass
class _SubscriptionMeta:
    id: str | None
    name: str | None
    avatar: str | None
    url: str


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')


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
    )


class _FakeTag:
    def __init__(self, attrs: dict[str, object] | None = None, text: str = ''):
        self._attrs = attrs or {}
        self.text = text

    def get(self, key: str, default=None):
        return self._attrs.get(key, default)


class _FakeSoup:
    def __init__(self, select_map: dict[str, list[object]] | None = None):
        self.select_map = select_map or {}

    def select(self, selector: str):
        return list(self.select_map.get(selector, []))

    def select_one(self, selector: str):
        items = self.select(selector)
        return items[0] if items else None


@contextmanager
def _stub_youporn_subscription_dependencies():
    originals = {name: sys.modules.get(name) for name in ('crawl', 'bs4')}

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


def _load_youporn_subscription_module():
    module_name = '_subscription_test_youporn'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, YOUPORN_SUBSCRIPTION_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


class YouPornSubscriptionTests(unittest.TestCase):
    def test_youporn_channel_get_subscribe_info_extracts_metadata(self):
        with _stub_youporn_subscription_dependencies() as (responses, soups):
            module = _load_youporn_subscription_module()

            responses.append(_FakeResponse('channel-page'))
            soups['channel-page'] = _FakeSoup({
                'h1.title-text': [_FakeTag(text='Bang Bros Network')],
                '.channel_subscription_button': [_FakeTag({'data-entityId': '6591731'})],
            })

            info = module.YouPornSubscription('https://www.youporn.com/channel/bangbrosnetwork/').get_subscribe_info()

            self.assertEqual(
                info,
                _SubscriptionMeta(
                    '6591731',
                    'Bang Bros Network',
                    None,
                    'https://www.youporn.com/channel/bangbrosnetwork/',
                ),
            )

    def test_youporn_full_sync_returns_continuation_cursor_for_next_page(self):
        with _stub_youporn_subscription_dependencies() as (responses, soups):
            module = _load_youporn_subscription_module()

            responses.append(_FakeResponse('page-1'))
            soups['page-1'] = _FakeSoup({
                'a[data-testid="plw_video_thumbnail_link"]': [
                    _FakeTag({'href': '/watch/221811351/demo-1/'}),
                    _FakeTag({'href': '/watch/221643281/demo-2/'}),
                ],
                'a.tm_pagination_link.pagination_number_link': [
                    _FakeTag({'data-page-number': '2', 'href': '/channel/bangbrosnetwork/?page=2'}),
                ],
            })

            subscription = module.YouPornSubscription('https://www.youporn.com/channel/bangbrosnetwork/')
            result = subscription.sync_videos(_SubscriptionSyncContext(mode='full'))

            self.assertEqual(
                result.video_urls,
                [
                    'https://www.youporn.com/watch/221811351/demo-1/',
                    'https://www.youporn.com/watch/221643281/demo-2/',
                ],
            )
            self.assertEqual(result.latest_video_url, 'https://www.youporn.com/watch/221811351/demo-1/')
            self.assertEqual(result.cursor_payload, {'page': 2})
            self.assertEqual(result.stop_reason, 'batch_exhausted')
            self.assertTrue(result.has_more)

    def test_youporn_incremental_sync_stops_at_last_seen_video(self):
        with _stub_youporn_subscription_dependencies() as (responses, soups):
            module = _load_youporn_subscription_module()

            responses.append(_FakeResponse('page-1'))
            soups['page-1'] = _FakeSoup({
                'a[data-testid="plw_video_thumbnail_link"]': [
                    _FakeTag({'href': '/watch/221811351/demo-1/'}),
                    _FakeTag({'href': '/watch/221643281/demo-2/'}),
                ],
                'a.tm_pagination_link.pagination_number_link': [],
            })

            subscription = module.YouPornSubscription('https://www.youporn.com/channel/bangbrosnetwork/')
            result = subscription.sync_videos(
                _SubscriptionSyncContext(
                    mode='incremental',
                    last_seen_video_url='https://www.youporn.com/watch/221643281/demo-2/',
                )
            )

            self.assertEqual(result.video_urls, ['https://www.youporn.com/watch/221811351/demo-1/'])
            self.assertEqual(result.latest_video_url, 'https://www.youporn.com/watch/221811351/demo-1/')
            self.assertEqual(result.stop_reason, 'cursor_hit')
            self.assertFalse(result.has_more)


if __name__ == '__main__':
    unittest.main()
