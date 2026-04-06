from fastapi.testclient import TestClient

from squirrel_cf_bypass.app.core.models import HtmlResult
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
        },
    )

    assert response.status_code == 200
    assert solver.calls[0]['proxy'] == 'http://127.0.0.1:7890'
    assert solver.calls[0]['custom_headers']['cookie'] == 'cf_clearance=demo; _jdb_session=session'
    assert solver.calls[0]['custom_headers']['referer'] == 'https://javdb.com/'
    assert solver.calls[0]['custom_headers']['origin'] == 'https://javdb.com'
    assert 'host' not in solver.calls[0]['custom_headers']


def test_cache_clear_endpoint_empties_runtime_state():
    solver = FakeSolver()
    client = TestClient(create_app(solver=solver))

    response = client.post('/cache/clear')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
