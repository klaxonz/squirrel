from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
JAVDB_HTML_CLIENT_PATH = REPO_ROOT / 'squirrel-site-runtimes' / 'javdb' / 'src' / 'squirrel_javdb' / 'html_client.py'


@contextmanager
def _stub_crawl_module():
    original = sys.modules.get('crawl')
    crawl_module = types.ModuleType('crawl')
    calls: list[tuple[str, str, dict]] = []

    crawl_module.filter_cookies_to_query_string = lambda _url: ''
    crawl_module.get_http_headers = lambda _slug, base=None: dict(base or {})
    crawl_module.get_login_headers = lambda _slug, base=None: dict(base or {})

    def request(method: str, url: str, **kwargs):
        calls.append((method, url, dict(kwargs)))
        raise RuntimeError('bypass unavailable')

    def request_without_limit(method: str, url: str, **kwargs):
        calls.append((method, url, dict(kwargs)))
        raise RuntimeError('bypass unavailable')

    crawl_module.request = request
    crawl_module.request_without_limit = request_without_limit

    try:
        sys.modules['crawl'] = crawl_module
        yield calls
    finally:
        if original is None:
            sys.modules.pop('crawl', None)
        else:
            sys.modules['crawl'] = original


def _load_html_client_module():
    module_name = '_javdb_html_client_test'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, JAVDB_HTML_CLIENT_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


class JavdbHtmlClientTests(unittest.TestCase):
    def test_fetch_javdb_html_requires_cloudflare_bypass(self):
        with _stub_crawl_module() as calls:
            module = _load_html_client_module()

            with self.assertRaisesRegex(RuntimeError, 'bypass unavailable'):
                module.fetch_javdb_html('https://javdb.com/actors/demo')

            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0], 'GET')
            self.assertEqual(calls[0][1], 'https://javdb.com/actors/demo')
            self.assertEqual(calls[0][2]['bypass_mode'], 'html')


if __name__ == '__main__':
    unittest.main()
