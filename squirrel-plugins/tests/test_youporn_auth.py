from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
YOUPORN_AUTH_PATH = REPO_ROOT / 'squirrel-plugins' / 'youporn' / 'src' / 'squirrel_youporn' / 'auth.py'


@dataclass
class _LoginStatusResult:
    site_name: str
    logged_in: bool
    message: str = ''
    username: str | None = None
    extra: dict | None = None


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200, url: str = 'https://www.youporn.com/'):
        self.text = text
        self.status_code = status_code
        self.url = url


@contextmanager
def _stub_youporn_auth_dependencies():
    originals = {name: sys.modules.get(name) for name in ('crawl',)}
    response_queue: list[_FakeResponse] = []

    crawl_module = types.ModuleType('crawl')
    crawl_module.LoginStatusResult = _LoginStatusResult
    crawl_module.filter_cookies_to_query_string = lambda _url: 'sid=demo'
    crawl_module.request_without_limit = lambda _method, _url, **_kwargs: response_queue.pop(0)
    crawl_module.get_login_config = lambda _site: {}
    crawl_module.get_login_headers = lambda _site, headers=None: dict(headers or {})

    try:
        sys.modules['crawl'] = crawl_module
        yield response_queue
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def _load_youporn_auth_module():
    module_name = '_auth_test_youporn'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, YOUPORN_AUTH_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


class YouPornAuthTests(unittest.TestCase):
    def test_youporn_login_status_detects_logged_in_username_from_page_params(self):
        with _stub_youporn_auth_dependencies() as responses:
            module = _load_youporn_auth_module()
            responses.append(
                _FakeResponse(
                    "<script>page_params.liu_username = 'demo_user'; page_params.isLoggedInUser = true;</script>"
                )
            )

            result = module.check_youporn_login_status()

            self.assertTrue(result.logged_in)
            self.assertEqual(result.username, 'demo_user')
            self.assertEqual(result.message, '已登录')

    def test_youporn_login_status_reports_logged_out_when_site_marks_user_as_guest(self):
        with _stub_youporn_auth_dependencies() as responses:
            module = _load_youporn_auth_module()
            responses.append(
                _FakeResponse(
                    "<script>page_params.liu_username = ''; page_params.isLoggedInUser = false;</script>"
                )
            )

            result = module.check_youporn_login_status()

            self.assertFalse(result.logged_in)
            self.assertEqual(result.message, '未登录')


if __name__ == '__main__':
    unittest.main()
