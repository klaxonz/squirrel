from fastapi.testclient import TestClient

from squirrel_cf_bypass.app.main import create_app


def test_health_reports_ok_defaults():
    client = TestClient(create_app())

    response = client.get('/health')

    assert response.status_code == 200
    assert response.json() == {
        'status': 'ok',
        'version': '0.1.0',
        'solver_ready': True,
        'cache_entries': 0,
        'session_entries': 0,
    }
