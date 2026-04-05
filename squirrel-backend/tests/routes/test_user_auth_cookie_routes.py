from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes.user import router
from utils.jwt_helper import AUTH_COOKIE_NAME


def _build_app(monkeypatch):
    app = FastAPI()
    app.include_router(router)
    monkeypatch.setattr(
        'routes.user.user_service.authenticate',
        lambda email, password: (
            type('UserStub', (), {'id': 7, 'to_dict': lambda self: {'id': 7, 'email': email}})(),
            object(),
        ),
    )
    monkeypatch.setattr('routes.user.create_access_token', lambda data, expires_delta=None: 'cookie-token')
    return app


def test_login_sets_http_only_auth_cookie(monkeypatch):
    client = TestClient(_build_app(monkeypatch))

    response = client.post('/api/users/login', json={'email': 'demo@example.com', 'password': 'secret'})

    assert response.status_code == 200
    assert response.json()['data'] == {'id': 7, 'email': 'demo@example.com'}
    assert response.cookies.get(AUTH_COOKIE_NAME) == 'cookie-token'
    set_cookie_header = response.headers['set-cookie'].lower()
    assert f'{AUTH_COOKIE_NAME}=cookie-token' in set_cookie_header
    assert 'httponly' in set_cookie_header
    assert 'secure' in set_cookie_header
    assert 'samesite=lax' in set_cookie_header


def test_logout_clears_auth_cookie(monkeypatch):
    client = TestClient(_build_app(monkeypatch))

    response = client.post('/api/users/logout')

    assert response.status_code == 200
    assert response.json()['msg'] == '退出成功'
    cleared_cookie = response.headers['set-cookie'].lower()
    assert f'{AUTH_COOKIE_NAME}=' in cleared_cookie
    assert 'max-age=0' in cleared_cookie or 'expires=' in cleared_cookie
