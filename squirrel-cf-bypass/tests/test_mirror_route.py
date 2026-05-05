from fastapi.testclient import TestClient

from squirrel_cf_bypass.app.core.models import MirrorResult
from squirrel_cf_bypass.app.main import create_app


class FakeSolver:
    async def fetch_html(self, *args, **kwargs):
        return None


class FakeService:
    def __init__(self):
        self.calls = []

    def health_payload(self):
        return {
            'status': 'ok',
            'version': '0.1.0',
            'solver_ready': True,
            'cache_entries': 0,
            'session_entries': 0,
        }

    async def clear_runtime_state(self):
        return None

    async def fetch_html(self, url, proxy=None, custom_headers=None):
        return None

    async def mirror_request(self, method, path, query_string, headers, body):
        self.calls.append({
            'method': method,
            'path': path,
            'query_string': query_string,
            'headers': headers,
            'body': body,
        })
        return MirrorResult(
            status_code=206,
            headers={'content-type': 'video/mp2t'},
            body=b'chunk',
        )


def test_mirror_route_requires_x_hostname():
    app = create_app(solver=FakeSolver())
    client = TestClient(app)

    response = client.get('/segments/demo.ts')

    assert response.status_code == 400
    assert response.json() == {'detail': 'x-hostname header is required'}


def test_mirror_route_proxies_any_path():
    app = create_app(solver=FakeSolver())
    app.state.bypass_service = FakeService()
    client = TestClient(app)

    response = client.get('/segments/demo.ts?token=1', headers={'x-hostname': 'surrit.com'})

    assert response.status_code == 206
    assert response.content == b'chunk'
    assert len(app.state.bypass_service.calls) == 1
    call = app.state.bypass_service.calls[0]
    assert call['method'] == 'GET'
    assert call['path'] == '/segments/demo.ts'
    assert call['query_string'] == 'token=1'
    assert call['body'] == b''
    assert call['headers']['host'] == 'testserver'
    assert call['headers']['user-agent'] == 'testclient'
    assert call['headers']['x-hostname'] == 'surrit.com'


def test_mirror_route_seeds_clearance_from_request_cookies(monkeypatch):
    session_calls = []

    class CookieSession:
        async def get(self, url, headers=None, allow_redirects=False):
            session_calls.append({
                'kind': 'seed',
                'url': url,
                'headers': headers,
                'allow_redirects': allow_redirects,
            })

            class Response:
                status_code = 200
                text = '<html>seed</html>'
                url = 'https://javdb.com/'
                cookies = {'cf_clearance': 'seeded'}

            return Response()

        async def request(self, method, url, headers=None, data=None, allow_redirects=False):
            session_calls.append({
                'kind': 'mirror',
                'method': method,
                'url': url,
                'headers': headers,
                'data': data,
                'allow_redirects': allow_redirects,
            })

            class Response:
                status_code = 200
                headers = {'content-type': 'text/plain'}
                content = b'ok'

            return Response()

    monkeypatch.setattr(
        'squirrel_cf_bypass.app.core.service.AsyncSession',
        lambda **kwargs: CookieSession(),
    )

    app = create_app(solver=FakeSolver())
    client = TestClient(app)

    response = client.get(
        '/videos/demo.m3u8',
        headers={
            'X-Hostname': 'javdb.com',
            'Cookie': 'cf_clearance=provided; _jdb_session=session',
            'User-Agent': 'Mirror UA',
        },
    )

    assert response.status_code == 200
    assert response.content == b'ok'
    assert session_calls[0]['kind'] == 'seed'
    assert session_calls[0]['url'] == 'https://javdb.com/'
    assert session_calls[0]['headers']['cookie'] == 'cf_clearance=provided; _jdb_session=session'
    assert session_calls[1]['kind'] == 'mirror'
    assert session_calls[1]['headers']['user-agent'] == 'Mirror UA'
    assert session_calls[1]['headers']['cookie'] == 'cf_clearance=seeded; _jdb_session=session'
