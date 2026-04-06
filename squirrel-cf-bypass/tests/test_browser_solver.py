import asyncio

import camoufox.async_api
import playwright_captcha

from playwright_captcha import CaptchaType

import squirrel_cf_bypass.app.core.browser_solver as browser_solver_module
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


def test_detect_captcha_type_prefers_turnstile_when_marker_present():
    solver = BrowserSolver()

    assert solver._detect_captcha_type(
        '<html><script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script></html>',
    ) is CaptchaType.CLOUDFLARE_TURNSTILE
    assert solver._detect_captcha_type(
        '<html><script src="/cdn-cgi/challenge-platform/h/b/orchestrate/chl_page/v1"></script></html>',
    ) is CaptchaType.CLOUDFLARE_INTERSTITIAL
    assert solver._detect_captcha_type('<html>ready</html>') is None


def test_detect_captcha_type_from_page_prefers_live_turnstile_markers():
    solver = BrowserSolver()

    class FakeLocator:
        def __init__(self, count):
            self._count = count

        async def count(self):
            return self._count

    class FakePage:
        def locator(self, selector):
            counts = {
                'input[name="cf-turnstile-response"]': 1,
                'script[src*="challenges.cloudflare.com/turnstile/v0"]': 1,
                'script[src*="/cdn-cgi/challenge-platform/"]': 1,
            }
            return FakeLocator(counts.get(selector, 0))

    result = asyncio.run(
        solver._detect_captcha_type_from_page(
            FakePage(),
            '<html><script src="/cdn-cgi/challenge-platform/h/b/orchestrate/chl_page/v1"></script></html>',
        )
    )

    assert result is CaptchaType.CLOUDFLARE_TURNSTILE


def test_build_camoufox_kwargs_applies_bypass_friendly_settings():
    solver = BrowserSolver()
    record = ClearanceRecord(
        cookies={'cf_clearance': 'demo'},
        user_agent='Mozilla/5.0 DemoUA',
        created_at=0.0,
        expires_at=1.0,
    )

    kwargs = solver._build_camoufox_kwargs(proxy='http://127.0.0.1:7890', cached_record=record)

    assert kwargs['headless'] is True
    assert kwargs['humanize'] is False
    assert kwargs['i_know_what_im_doing'] is True
    assert kwargs['disable_coop'] is True
    assert kwargs['main_world_eval'] is True
    assert kwargs['block_webrtc'] is True
    assert kwargs['enable_cache'] is False
    assert kwargs['geoip'] is True
    assert kwargs['addons']
    assert kwargs['config']['forceScopeAccess'] is True
    assert kwargs['config']['navigator.userAgent'] == 'Mozilla/5.0 DemoUA'


def test_fetch_html_prefers_interstitial_solver_for_managed_challenge(monkeypatch):
    calls = {}

    class FakePage:
        def __init__(self):
            self.url = 'https://missav.ai/search/DMOW-227'
            self.solved = False

        async def goto(self, url, wait_until, timeout):
            calls['goto'] = {'url': url, 'wait_until': wait_until, 'timeout': timeout}

        async def title(self):
            return 'MissAV Search' if self.solved else 'Just a moment...'

        async def content(self):
            if self.solved:
                return '<html>resolved</html>'
            return '<html><script src="/cdn-cgi/challenge-platform/h/b/orchestrate/chl_page/v1"></script></html>'

        async def evaluate(self, expression):
            assert expression == 'navigator.userAgent'
            return 'FakeUA/1.0'

        def locator(self, selector):
            counts = {
                'input[name="cf-turnstile-response"]': 1,
                'script[src*="challenges.cloudflare.com/turnstile/v0"]': 1,
                'script[src*="/cdn-cgi/challenge-platform/"]': 1,
            }
            return FakeLocator(counts.get(selector, 0))

    class FakeLocator:
        def __init__(self, count):
            self._count = count

        async def count(self):
            return self._count

    class FakeContext:
        def __init__(self):
            self.page = FakePage()

        async def new_page(self):
            return self.page

        async def cookies(self):
            return [{'name': 'cf_clearance', 'value': 'token'}]

    class FakeBrowser:
        def __init__(self):
            self.context = FakeContext()

        async def new_context(self, **kwargs):
            calls['new_context'] = kwargs
            return self.context

    class FakeAsyncCamoufox:
        def __init__(self, **kwargs):
            calls['camoufox_init'] = kwargs
            self.browser = FakeBrowser()

        async def __aenter__(self):
            return self.browser

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeClickSolver:
        def __init__(self, **kwargs):
            calls['click_solver_init'] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def solve_captcha(self, captcha_container, captcha_type, **kwargs):
            captcha_container.solved = True
            calls['solve_captcha'] = {
                'captcha_container': captcha_container,
                'captcha_type': captcha_type,
                'kwargs': kwargs,
            }
            return True

    class FakeFrameworkType:
        CAMOUFOX = 'camoufox'

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr(camoufox.async_api, 'AsyncCamoufox', FakeAsyncCamoufox)
    monkeypatch.setattr(playwright_captcha, 'ClickSolver', FakeClickSolver)
    monkeypatch.setattr(playwright_captcha, 'FrameworkType', FakeFrameworkType)
    monkeypatch.setattr(browser_solver_module.asyncio, 'sleep', fake_sleep)

    result = asyncio.run(BrowserSolver().fetch_html('https://missav.ai/search/DMOW-227'))

    assert result is not None
    assert result.html == '<html>resolved</html>'
    assert result.cookies == {'cf_clearance': 'token'}
    assert calls['camoufox_init']['disable_coop'] is True
    assert calls['camoufox_init']['main_world_eval'] is True
    assert calls['camoufox_init']['addons']
    assert calls['camoufox_init']['config']['forceScopeAccess'] is True
    assert calls['solve_captcha']['captcha_type'] is CaptchaType.CLOUDFLARE_INTERSTITIAL
    assert calls['solve_captcha']['kwargs'] == {'expected_content_selector': '#root'}


def test_fetch_html_waits_for_auto_bypass_before_solver(monkeypatch):
    calls = {}

    class FakePage:
        def __init__(self):
            self.url = 'https://missav.ai/search/DMOW-227'
            self._checks = 0

        async def goto(self, url, wait_until, timeout):
            return None

        async def title(self):
            self._checks += 1
            return 'MissAV Search' if self._checks >= 3 else 'Just a moment...'

        async def content(self):
            return '<html>resolved</html>' if self._checks >= 3 else '<html><script src="/cdn-cgi/challenge-platform/h/b/orchestrate/chl_page/v1"></script></html>'

        async def evaluate(self, expression):
            assert expression == 'navigator.userAgent'
            return 'FakeUA/1.0'

        def locator(self, selector):
            return FakeLocator(0)

    class FakeLocator:
        def __init__(self, count):
            self._count = count

        async def count(self):
            return self._count

    class FakeContext:
        def __init__(self):
            self.page = FakePage()

        async def new_page(self):
            return self.page

        async def cookies(self):
            return [{'name': 'cf_clearance', 'value': 'token'}]

    class FakeBrowser:
        def __init__(self):
            self.context = FakeContext()

        async def new_context(self, **kwargs):
            return self.context

    class FakeAsyncCamoufox:
        def __init__(self, **kwargs):
            self.browser = FakeBrowser()

        async def __aenter__(self):
            return self.browser

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeClickSolver:
        def __init__(self, **kwargs):
            calls['solver_init'] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def solve_captcha(self, captcha_container, captcha_type, **kwargs):
            raise AssertionError('solver should not be used after auto bypass')

    class FakeFrameworkType:
        CAMOUFOX = 'camoufox'

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr(camoufox.async_api, 'AsyncCamoufox', FakeAsyncCamoufox)
    monkeypatch.setattr(playwright_captcha, 'ClickSolver', FakeClickSolver)
    monkeypatch.setattr(playwright_captcha, 'FrameworkType', FakeFrameworkType)
    monkeypatch.setattr(browser_solver_module.asyncio, 'sleep', fake_sleep)

    result = asyncio.run(BrowserSolver().fetch_html('https://missav.ai/search/DMOW-227'))

    assert result is not None
    assert result.html == '<html>resolved</html>'
    assert 'solver_init' not in calls


def test_fetch_html_uses_manual_turnstile_click_fallback(monkeypatch):
    calls = {'ups': 0}

    class FakeMouse:
        def __init__(self, page):
            self._page = page

        async def move(self, x, y, steps=1):
            return None

        async def down(self):
            return None

        async def up(self):
            calls['ups'] += 1
            self._page.solved = True
            return None

        async def click(self, x, y):
            self._page.solved = True
            return None

    class FakePage:
        def __init__(self):
            self.url = 'https://missav.ai/search/DMOW-227'
            self.solved = False
            self.mouse = FakeMouse(self)

        async def goto(self, url, wait_until, timeout):
            calls['goto'] = {'url': url, 'wait_until': wait_until, 'timeout': timeout}

        async def title(self):
            return 'MissAV Search' if self.solved else 'Just a moment...'

        async def content(self):
            if self.solved:
                return '<html>resolved</html>'
            return '<html>Please complete the captcha<script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script></html>'

        async def evaluate(self, expression):
            if expression == 'navigator.userAgent':
                return 'FakeUA/1.0'
            return {'x': 200, 'y': 300, 'width': 120, 'height': 60}

        def locator(self, selector):
            counts = {
                'input[name="cf-turnstile-response"]': 1,
                'script[src*="challenges.cloudflare.com/turnstile/v0"]': 1,
                'script[src*="/cdn-cgi/challenge-platform/"]': 1,
            }
            return FakeLocator(counts.get(selector, 0))

    class FakeLocator:
        def __init__(self, count):
            self._count = count

        async def count(self):
            return self._count

    class FakeContext:
        def __init__(self):
            self.page = FakePage()

        async def new_page(self):
            return self.page

        async def cookies(self):
            return [{'name': 'cf_clearance', 'value': 'token'}] if self.page.solved else []

    class FakeBrowser:
        def __init__(self):
            self.context = FakeContext()

        async def new_context(self, **kwargs):
            return self.context

    class FakeAsyncCamoufox:
        def __init__(self, **kwargs):
            self.browser = FakeBrowser()

        async def __aenter__(self):
            return self.browser

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeClickSolver:
        def __init__(self, **kwargs):
            calls['solver_init'] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def solve_captcha(self, captcha_container, captcha_type, **kwargs):
            raise AssertionError('manual fallback should resolve before solver is used')

    class FakeFrameworkType:
        CAMOUFOX = 'camoufox'

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr(camoufox.async_api, 'AsyncCamoufox', FakeAsyncCamoufox)
    monkeypatch.setattr(playwright_captcha, 'ClickSolver', FakeClickSolver)
    monkeypatch.setattr(playwright_captcha, 'FrameworkType', FakeFrameworkType)
    monkeypatch.setattr(browser_solver_module.asyncio, 'sleep', fake_sleep)

    result = asyncio.run(BrowserSolver().fetch_html('https://missav.ai/search/DMOW-227'))

    assert result is not None
    assert result.html == '<html>resolved</html>'
    assert result.cookies == {'cf_clearance': 'token'}
    assert calls['ups'] >= 1
    assert 'solver_init' not in calls


def test_fetch_html_returns_none_when_challenge_page_persists(monkeypatch):
    class FakePage:
        def __init__(self):
            self.url = 'https://missav.ai/search/DMOW-227'

        async def goto(self, url, wait_until, timeout):
            return None

        async def title(self):
            return 'Just a moment...'

        async def content(self):
            return '<html>Please complete the captcha<script>window.__cf_chl_opt = {}</script></html>'

        async def evaluate(self, expression):
            assert expression == 'navigator.userAgent'
            return 'FakeUA/1.0'

    class FakeContext:
        def __init__(self):
            self.page = FakePage()

        async def new_page(self):
            return self.page

        async def cookies(self):
            return []

    class FakeBrowser:
        def __init__(self):
            self.context = FakeContext()

        async def new_context(self, **kwargs):
            return self.context

    class FakeAsyncCamoufox:
        def __init__(self, **kwargs):
            self.browser = FakeBrowser()

        async def __aenter__(self):
            return self.browser

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeClickSolver:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def __init__(self, **kwargs):
            return None

        async def solve_captcha(self, captcha_container, captcha_type, **kwargs):
            return True

    class FakeFrameworkType:
        CAMOUFOX = 'camoufox'

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr(camoufox.async_api, 'AsyncCamoufox', FakeAsyncCamoufox)
    monkeypatch.setattr(playwright_captcha, 'ClickSolver', FakeClickSolver)
    monkeypatch.setattr(playwright_captcha, 'FrameworkType', FakeFrameworkType)
    monkeypatch.setattr(browser_solver_module.asyncio, 'sleep', fake_sleep)

    result = asyncio.run(BrowserSolver().fetch_html('https://missav.ai/search/DMOW-227'))

    assert result is None


def test_fetch_html_returns_none_when_solver_raises(monkeypatch):
    class FakePage:
        def __init__(self):
            self.url = 'https://missav.ai/search/DMOW-227'

        async def goto(self, url, wait_until, timeout):
            return None

        async def title(self):
            return 'Just a moment...'

        async def content(self):
            return '<html><script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script></html>'

        async def evaluate(self, expression):
            assert expression == 'navigator.userAgent'
            return 'FakeUA/1.0'

    class FakeContext:
        def __init__(self):
            self.page = FakePage()

        async def new_page(self):
            return self.page

        async def cookies(self):
            return []

    class FakeBrowser:
        def __init__(self):
            self.context = FakeContext()

        async def new_context(self, **kwargs):
            return self.context

    class FakeAsyncCamoufox:
        def __init__(self, **kwargs):
            self.browser = FakeBrowser()

        async def __aenter__(self):
            return self.browser

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeClickSolver:
        def __init__(self, **kwargs):
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def solve_captcha(self, captcha_container, captcha_type, **kwargs):
            raise RuntimeError('solver boom')

    class FakeFrameworkType:
        CAMOUFOX = 'camoufox'

    monkeypatch.setattr(camoufox.async_api, 'AsyncCamoufox', FakeAsyncCamoufox)
    monkeypatch.setattr(playwright_captcha, 'ClickSolver', FakeClickSolver)
    monkeypatch.setattr(playwright_captcha, 'FrameworkType', FakeFrameworkType)

    result = asyncio.run(BrowserSolver().fetch_html('https://missav.ai/search/DMOW-227'))

    assert result is None
