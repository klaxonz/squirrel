from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PORNHUB_AUTH_PATH = REPO_ROOT / 'squirrel-plugins' / 'pornhub' / 'src' / 'squirrel_pornhub' / 'auth.py'


@dataclass
class _LoginStatusResult:
    site_name: str
    logged_in: bool
    message: str = ''
    username: str | None = None
    extra: dict | None = None


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200, url: str = 'https://www.pornhub.com/'):
        self.text = text
        self.status_code = status_code
        self.url = url


@contextmanager
def _stub_pornhub_auth_dependencies():
    originals = {name: sys.modules.get(name) for name in ('crawl',)}
    response_queue: list[object] = []

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


def _load_pornhub_auth_module():
    module_name = '_auth_test_pornhub'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, PORNHUB_AUTH_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


class PornhubAuthTests(unittest.TestCase):
    def test_pornhub_login_status_detects_logged_in_profile_menu(self):
        with _stub_pornhub_auth_dependencies() as responses:
            module = _load_pornhub_auth_module()
            responses.append(
                _FakeResponse(
                    '<div class="profile"><div class="profileData">'
                    '<a class="username" href="/users/demo_user">'
                    '<span class="wrapUserProfileData"><span class="js_userName">demo_user</span></span>'
                    '<span class="userUserStatus updatedText">See Your Profile</span>'
                    '</a></div></div>'
                )
            )

            result = module.check_pornhub_login_status()

            self.assertTrue(result.logged_in)
            self.assertEqual(result.username, 'demo_user')
            self.assertEqual(result.message, '已登录')

    def test_pornhub_login_status_marks_challenge_page_as_check_failure(self):
        with _stub_pornhub_auth_dependencies() as responses:
            module = _load_pornhub_auth_module()
            responses.append(
                _FakeResponse(
                    '<html><head><script type="text/javascript">'
                    "function leastFactor(n) { return n; }"
                    "if (typeof phantom !== 'undefined') return 'phantom';"
                    "if (typeof module !== 'undefined' && module.exports) return 'node';"
                    '</script></head><body></body></html>'
                )
            )

            result = module.check_pornhub_login_status()

            self.assertFalse(result.logged_in)
            self.assertEqual(result.message, '检测失败: 返回内容显示为站点验证页')
            self.assertEqual(result.extra, {'transient_failure': True})

    def test_pornhub_login_status_marks_403_as_check_failure(self):
        with _stub_pornhub_auth_dependencies() as responses:
            module = _load_pornhub_auth_module()
            responses.append(_FakeResponse('', status_code=403))

            result = module.check_pornhub_login_status()

            self.assertFalse(result.logged_in)
            self.assertEqual(result.message, '检测失败: 被拒绝访问 (status=403)')
            self.assertEqual(result.extra, {'transient_failure': True})


if __name__ == '__main__':
    unittest.main()
