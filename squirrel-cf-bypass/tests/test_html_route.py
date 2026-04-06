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


def test_cache_clear_endpoint_empties_runtime_state():
    solver = FakeSolver()
    client = TestClient(create_app(solver=solver))

    response = client.post('/cache/clear')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
