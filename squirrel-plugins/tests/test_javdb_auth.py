from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
JAVDB_AUTH_PATH = REPO_ROOT / 'squirrel-plugins' / 'javdb' / 'src' / 'squirrel_javdb' / 'auth.py'


@dataclass
class _LoginStatusResult:
    site_name: str
    logged_in: bool
    message: str = ''
    username: str | None = None
    extra: dict | None = None


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200, headers: dict[str, str] | None = None):
        self.text = text
        self.status_code = status_code
        self.headers = headers or {}


@contextmanager
def _stub_javdb_auth_dependencies():
    originals = {
        name: sys.modules.get(name)
        for name in ('crawl', 'squirrel_javdb', 'squirrel_javdb.html_client')
    }
    response_queue: list[object] = []

    crawl_module = types.ModuleType('crawl')
    crawl_module.LoginStatusResult = _LoginStatusResult
    crawl_module.get_login_config = lambda _site: {}

    package_module = types.ModuleType('squirrel_javdb')
    package_module.__path__ = [str(JAVDB_AUTH_PATH.parent)]

    html_client_module = types.ModuleType('squirrel_javdb.html_client')

    def build_javdb_headers(_url: str, *, login: bool = False):
        _ = login
        return {'Cookie': 'session=demo'}

    def fetch_javdb_html(_url: str, **_kwargs):
        if not response_queue:
            raise AssertionError('No queued response for fetch_javdb_html')
        item = response_queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    html_client_module.DEFAULT_JAVDB_TIMEOUT_SECONDS = 30.0
    html_client_module.build_javdb_headers = build_javdb_headers
    html_client_module.fetch_javdb_html = fetch_javdb_html

    try:
        sys.modules['crawl'] = crawl_module
        sys.modules['squirrel_javdb'] = package_module
        sys.modules['squirrel_javdb.html_client'] = html_client_module
        yield response_queue
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def _load_javdb_auth_module():
    module_name = 'squirrel_javdb.auth'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, JAVDB_AUTH_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


class JavdbAuthTests(unittest.TestCase):
    def test_javdb_login_status_marks_gateway_error_page_as_check_failure(self):
        with _stub_javdb_auth_dependencies() as responses:
            module = _load_javdb_auth_module()
            responses.append(_FakeResponse(
                '<html><head><title>javdb.com | 502: Bad gateway</title></head>'
                '<body><div id="cf-error-details"></div></body></html>'
            ))

            result = module.check_javdb_login_status()

            self.assertFalse(result.logged_in)
            self.assertEqual(result.message, '检测失败: 返回内容显示为站点错误页')
            self.assertEqual(result.extra, {'transient_failure': True})

    def test_javdb_login_status_marks_request_exceptions_as_check_failure(self):
        with _stub_javdb_auth_dependencies() as responses:
            module = _load_javdb_auth_module()
            responses.append(RuntimeError('temporary upstream failure'))

            result = module.check_javdb_login_status()

            self.assertFalse(result.logged_in)
            self.assertEqual(result.message, '检测失败: 请求失败: temporary upstream failure')
            self.assertEqual(result.extra, {'transient_failure': True})


if __name__ == '__main__':
    unittest.main()
