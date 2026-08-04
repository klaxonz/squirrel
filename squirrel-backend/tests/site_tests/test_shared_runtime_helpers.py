from __future__ import annotations

import importlib
import sys
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_CRAWL_ROOT = REPO_ROOT / 'sites' / 'crawl'


@contextmanager
def _stub_shared_crawl_package():
    originals = {
        name: module
        for name, module in sys.modules.items()
        if name == 'sites.crawl' or name.startswith('sites.crawl.')
    }
    package_module = types.ModuleType('sites.crawl')
    package_module.__path__ = [str(SHARED_CRAWL_ROOT)]

    try:
        for name in list(originals):
            sys.modules.pop(name, None)
        sys.modules['sites.crawl'] = package_module
        yield
    finally:
        for name in list(sys.modules):
            if name == 'sites.crawl' or name.startswith('sites.crawl.'):
                sys.modules.pop(name, None)
        sys.modules.update(originals)


class SharedRuntimeHelperTests(unittest.TestCase):
    def test_shared_cookie_helper_uses_youtube_cookie_domain_for_googlevideo_urls(self):
        with _stub_shared_crawl_package():
            utils_module = importlib.import_module('sites.crawl.utils')

        with TemporaryDirectory() as temp_dir:
            cookie_file = Path(temp_dir) / 'cookies.txt'
            cookie_file.write_text(
                '# Netscape HTTP Cookie File\n'
                '.youtube.com\tTRUE\t/\tFALSE\t2147483647\tSID\tabc123\n'
                '.googlevideo.com\tTRUE\t/\tFALSE\t2147483647\tGV\tignored\n',
                encoding='utf-8',
            )

            utils_module.configure_cookie_file_resolver(lambda _url: str(cookie_file))
            utils_module.configure_cookie_domain_resolver(lambda _url: 'youtube.com')

            self.assertEqual(
                utils_module.filter_cookies_to_query_string(
                    'https://rr4---sn-a5meknzl.googlevideo.com/videoplayback?c=MWEB',
                ),
                'SID=abc123',
            )

    def test_subscription_helpers_deduplicate_urls_and_build_cursor_payload(self):
        with _stub_shared_crawl_package():
            module = importlib.import_module('sites.crawl.subscription_helpers')
            core_module = importlib.import_module('sites.crawl.core')

        context = core_module.SubscriptionSyncContext(
            mode='incremental',
            cursor_payload={'page': 1},
            last_seen_video_url='https://example.com/watch?v=seen',
            limit=5,
        )
        limit = module.resolve_subscription_limit(context)
        video_urls: list[str] = []
        seen_urls: set[str] = set()
        latest_video_url = None

        latest_video_url, stop_reason = module.append_subscription_video_url(
            'https://example.com/watch?v=new',
            video_urls=video_urls,
            seen_urls=seen_urls,
            context=context,
            latest_video_url=latest_video_url,
            limit=limit,
        )
        self.assertIsNone(stop_reason)

        latest_video_url, stop_reason = module.append_subscription_video_url(
            'https://example.com/watch?v=new',
            video_urls=video_urls,
            seen_urls=seen_urls,
            context=context,
            latest_video_url=latest_video_url,
            limit=limit,
        )
        self.assertIsNone(stop_reason)

        latest_video_url, stop_reason = module.append_subscription_video_url(
            'https://example.com/watch?v=seen',
            video_urls=video_urls,
            seen_urls=seen_urls,
            context=context,
            latest_video_url=latest_video_url,
            limit=limit,
        )

        self.assertEqual(video_urls, ['https://example.com/watch?v=new'])
        self.assertEqual(latest_video_url, 'https://example.com/watch?v=new')
        self.assertEqual(stop_reason, 'cursor_hit')

        result = module.build_subscription_sync_result(
            video_urls=video_urls,
            latest_video_url=latest_video_url,
            context=context,
            stop_reason=stop_reason,
        )
        self.assertEqual(result.cursor_payload, {'latest_video_url': 'https://example.com/watch?v=new'})
        self.assertIsNone(result.total_available)

    def test_build_subscription_sync_result_preserves_explicit_batch_cursor(self):
        with _stub_shared_crawl_package():
            module = importlib.import_module('sites.crawl.subscription_helpers')
            core_module = importlib.import_module('sites.crawl.core')

        context = core_module.SubscriptionSyncContext(
            mode='full',
            cursor_payload={'page': 1},
        )

        result = module.build_subscription_sync_result(
            video_urls=['https://example.com/watch?v=1'],
            latest_video_url='https://example.com/watch?v=1',
            context=context,
            stop_reason='batch_exhausted',
            cursor_payload={'page': 2},
            has_more=True,
        )

        self.assertTrue(result.has_more)
        self.assertEqual(result.cursor_payload, {'page': 2})
        self.assertEqual(result.stop_reason, 'batch_exhausted')

    def test_build_subscription_sync_result_preserves_explicit_gap_detection_fields(self):
        with _stub_shared_crawl_package():
            module = importlib.import_module('sites.crawl.subscription_helpers')
            core_module = importlib.import_module('sites.crawl.core')

        context = core_module.SubscriptionSyncContext(
            mode='incremental',
            cursor_payload={'latest_video_url': 'https://example.com/watch?v=seen'},
            last_seen_video_url='https://example.com/watch?v=seen',
        )

        result = module.build_subscription_sync_result(
            video_urls=['https://example.com/watch?v=new'],
            latest_video_url='https://example.com/watch?v=new',
            context=context,
            stop_reason='cursor_hit',
            total_available=42,
            head_sample_urls=[
                'https://example.com/watch?v=new',
                'https://example.com/watch?v=seen',
            ],
            anchor_found=True,
        )

        self.assertEqual(result.total_available, 42)
        self.assertEqual(
            result.head_sample_urls,
            [
                'https://example.com/watch?v=new',
                'https://example.com/watch?v=seen',
            ],
        )
        self.assertIs(result.anchor_found, True)


if __name__ == '__main__':
    unittest.main()
