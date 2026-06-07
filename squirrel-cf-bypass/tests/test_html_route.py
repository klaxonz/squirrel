import time

from fastapi.testclient import TestClient

from squirrel_cf_bypass.app.core.models import ClearanceRecord, HtmlResult
from squirrel_cf_bypass.app.main import create_app


class FakeSolver:
    def __init__(self):
        self.calls = []

    async def fetch_html(self, url, proxy=None, cached_record=None, custom_headers=None):
        self.calls.append({
            'url': url,
            'proxy': proxy,
            'cached_record': cached_record,
            'custom_headers': custom_headers,
        })
        return HtmlResult(
            html='<html>ok</html>',
            final_url='https://javdb.com/?via=solver',
            status_code=200,
            cookies={'cf_clearance': 'demo'},
            user_agent='UA',
        )


def test_html_route_returns_solver_result_headers():
    solver = FakeSolver()
    client = TestClient(create_app(solver=solver))

    response = client.get('/html', params={'url': 'https://javdb.com'})

    assert response.status_code == 200
    assert response.text == '<html>ok</html>'
    assert response.headers['x-cf-bypasser-final-url'] == 'https://javdb.com/?via=solver'
    assert response.headers['x-cf-bypasser-user-agent'] == 'UA'
    assert response.headers['x-cf-bypasser-source'] == 'solver'
    assert solver.calls[0]['url'] == 'https://javdb.com'


def test_html_route_forwards_request_headers_to_solver():
    solver = FakeSolver()
    client = TestClient(create_app(solver=solver))

    response = client.get(
        '/html',
        params={'url': 'https://javdb.com/users/collection_actors?page=1'},
        headers={
            'Cookie': 'cf_clearance=demo; _jdb_session=session',
            'Referer': 'https://javdb.com/',
            'Origin': 'https://javdb.com',
            'X-Proxy': 'http://127.0.0.1:7890',
            'X-Bypass-Cache': 'true',
        },
    )

    assert response.status_code == 200
    assert solver.calls[0]['proxy'] == 'http://127.0.0.1:7890'
    assert solver.calls[0]['custom_headers']['cookie'] == 'cf_clearance=demo; _jdb_session=session'
    assert solver.calls[0]['custom_headers']['referer'] == 'https://javdb.com/'
    assert solver.calls[0]['custom_headers']['origin'] == 'https://javdb.com'
    assert 'host' not in solver.calls[0]['custom_headers']
    assert 'x-bypass-cache' not in solver.calls[0]['custom_headers']


def test_html_route_uses_cached_clearance_without_solver(monkeypatch):
    session_calls = []

    class CachedSession:
        async def get(self, url, headers=None, allow_redirects=False):
            session_calls.append({
                'url': url,
                'headers': headers,
                'allow_redirects': allow_redirects,
            })

            class Response:
                status_code = 200
                text = '<html>cached</html>'
                url = 'https://javdb.com/page'

            return Response()

    monkeypatch.setattr(
        'squirrel_cf_bypass.app.core.service.AsyncSession',
        lambda **kwargs: CachedSession(),
    )

    solver = FakeSolver()
    app = create_app(solver=solver)
    app.state.bypass_service._cache.set(
        'javdb.com',
        None,
        ClearanceRecord(
            cookies={'cf_clearance': 'cached'},
            user_agent='Cached UA',
            created_at=time.time(),
            expires_at=time.time() + 60,
        ),
    )
    client = TestClient(app)

    response = client.get(
        '/html',
        params={'url': 'https://javdb.com/page'},
        headers={'Referer': 'https://javdb.com/'},
    )

    assert response.status_code == 200
    assert response.text == '<html>cached</html>'
    assert response.headers['x-cf-bypasser-source'] == 'cache'
    assert solver.calls == []
    assert len(session_calls) == 1
    assert session_calls[0]['allow_redirects'] is True
    assert session_calls[0]['headers']['user-agent'] == 'Cached UA'
    assert session_calls[0]['headers']['cookie'] == 'cf_clearance=cached'
    assert session_calls[0]['headers']['referer'] == 'https://javdb.com/'


def test_html_route_seeds_cache_from_provided_cookies(monkeypatch):
    session_calls = []

    class CookieSession:
        async def get(self, url, headers=None, allow_redirects=False):
            session_calls.append({
                'url': url,
                'headers': headers,
                'allow_redirects': allow_redirects,
            })

            class Response:
                status_code = 200
                text = '<html>provided</html>'
                url = 'https://javdb.com/page'
                cookies = {'cf_clearance': 'refreshed'}

            return Response()

    monkeypatch.setattr(
        'squirrel_cf_bypass.app.core.service.AsyncSession',
        lambda **kwargs: CookieSession(),
    )

    solver = FakeSolver()
    app = create_app(solver=solver)
    client = TestClient(app)

    response = client.get(
        '/html',
        params={'url': 'https://javdb.com/page'},
        headers={
            'Cookie': 'cf_clearance=provided; _jdb_session=session',
            'User-Agent': 'Provided UA',
        },
    )

    assert response.status_code == 200
    assert response.text == '<html>provided</html>'
    assert response.headers['x-cf-bypasser-source'] == 'provided-cookie'
    assert solver.calls == []
    assert session_calls[0]['allow_redirects'] is True
    assert session_calls[0]['headers']['cookie'] == 'cf_clearance=provided; _jdb_session=session'
    cached = app.state.bypass_service._cache.get('javdb.com', None)
    assert cached.cookies == {'cf_clearance': 'refreshed', '_jdb_session': 'session'}
    assert cached.user_agent == 'Provided UA'


def test_html_route_invalidates_challenge_cache_and_falls_back_to_solver(monkeypatch):
    session_calls = []

    class ChallengeSession:
        async def get(self, url, headers=None, allow_redirects=False):
            session_calls.append({
                'url': url,
                'headers': headers,
                'allow_redirects': allow_redirects,
            })

            class Response:
                status_code = 403
                text = '<html><title>Just a moment...</title></html>'
                url = 'https://javdb.com/page'

            return Response()

    monkeypatch.setattr(
        'squirrel_cf_bypass.app.core.service.AsyncSession',
        lambda **kwargs: ChallengeSession(),
    )

    solver = FakeSolver()
    app = create_app(solver=solver)
    app.state.bypass_service._cache.set(
        'javdb.com',
        None,
        ClearanceRecord(
            cookies={'cf_clearance': 'stale'},
            user_agent='Stale UA',
            created_at=time.time(),
            expires_at=time.time() + 60,
            browser_config={'navigator.userAgent': 'Stale UA'},
            browser_os='windows',
        ),
    )
    client = TestClient(app)

    response = client.get('/html', params={'url': 'https://javdb.com/page'})

    assert response.status_code == 200
    assert response.text == '<html>ok</html>'
    assert len(solver.calls) == 1
    assert solver.calls[0]['cached_record'] is not None
    assert solver.calls[0]['cached_record'].browser_config == {'navigator.userAgent': 'Stale UA'}
    assert solver.calls[0]['cached_record'].browser_os == 'windows'
    assert app.state.bypass_service._cache.get('javdb.com', None).cookies == {'cf_clearance': 'demo'}
    assert app.state.bypass_service._cache.get('javdb.com', None).http_usable is False
    assert len(session_calls) == 1

    response = client.get('/html', params={'url': 'https://javdb.com/page'})

    assert response.status_code == 200
    assert len(solver.calls) == 2
    assert solver.calls[1]['cached_record'] is not None
    assert len(session_calls) == 1


def test_html_route_can_force_cache_bypass():
    solver = FakeSolver()
    app = create_app(solver=solver)
    app.state.bypass_service._cache.set(
        'javdb.com',
        None,
        ClearanceRecord(
            cookies={'cf_clearance': 'cached'},
            user_agent='Cached UA',
            created_at=time.time(),
            expires_at=time.time() + 60,
        ),
    )
    client = TestClient(app)

    response = client.get(
        '/html',
        params={'url': 'https://javdb.com/page'},
        headers={'X-Bypass-Cache': 'true'},
    )

    assert response.status_code == 200
    assert len(solver.calls) == 1
    assert solver.calls[0]['cached_record'] is None
    assert 'x-bypass-cache' not in solver.calls[0]['custom_headers']


def test_html_route_returns_502_when_solver_cannot_bypass():
    class NullSolver(FakeSolver):
        async def fetch_html(self, url, proxy=None, cached_record=None, custom_headers=None):
            self.calls.append({
                'url': url,
                'proxy': proxy,
                'cached_record': cached_record,
                'custom_headers': custom_headers,
            })
            return None

    solver = NullSolver()
    client = TestClient(create_app(solver=solver))

    response = client.get('/html', params={'url': 'https://missav.ai/search/DMOW-227'})

    assert response.status_code == 502
    assert response.json() == {'detail': 'Failed to bypass Cloudflare protection'}


def test_cache_clear_endpoint_empties_runtime_state():
    solver = FakeSolver()
    client = TestClient(create_app(solver=solver))

    response = client.post('/cache/clear')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
