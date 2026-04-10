from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes.middleware.auth import AuthMiddleware
from utils.jwt_helper import AUTH_COOKIE_NAME


def _build_app(monkeypatch):
    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get('/api/private')
    async def private_api():
        return JSONResponse({'ok': True})

    monkeypatch.setattr('routes.middleware.auth.validate_auth_token', lambda token: ({'sub': '7', 'tv': 0}, object()))
    return app


def test_private_api_accepts_cookie_auth(monkeypatch):
    client = TestClient(_build_app(monkeypatch))

    response = client.get('/api/private', cookies={AUTH_COOKIE_NAME: 'cookie-token'})

    assert response.status_code == 200
    assert response.json() == {'ok': True}


def test_private_api_rejects_bearer_header_without_cookie(monkeypatch):
    client = TestClient(_build_app(monkeypatch))

    response = client.get('/api/private', headers={'Authorization': 'Bearer legacy-token'})

    assert response.status_code == 401
    assert response.json()['msg'] == '请先登录'
