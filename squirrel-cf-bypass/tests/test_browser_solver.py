import asyncio

from squirrel_cf_bypass.app.core.browser_solver import BrowserSolver
from squirrel_cf_bypass.app.core.models import ClearanceRecord


class FakeContext:
    def __init__(self):
        self.calls = []

    async def add_cookies(self, cookies):
        self.calls.append(cookies)


def test_restore_cached_cookies_uses_target_url():
    solver = BrowserSolver()
    context = FakeContext()
    record = ClearanceRecord(
        cookies={'cf_clearance': 'demo', '__cf_bm': 'bm'},
        user_agent='UA',
        created_at=0.0,
        expires_at=1.0,
    )

    asyncio.run(solver._restore_cached_cookies(context, 'https://javdb.com/video', record))

    assert context.calls == [[
        {'name': 'cf_clearance', 'value': 'demo', 'url': 'https://javdb.com/video'},
        {'name': '__cf_bm', 'value': 'bm', 'url': 'https://javdb.com/video'},
    ]]


def test_is_challenge_page_matches_known_titles():
    solver = BrowserSolver()

    assert solver._is_challenge_page('Just a moment...', '<html></html>') is True
    assert solver._is_challenge_page('Welcome', '<html>Please complete the captcha</html>') is True
    assert solver._is_challenge_page('Welcome', '<html>ready</html>') is False
