import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes import user as user_routes
from utils.jwt_helper import AUTH_COOKIE_NAME


def _make_user(user_id=7, email="demo@example.com", token_version=0):
    def _to_dict(self, exclude=None, **kwargs):
        _ = kwargs
        data = {"id": user_id, "email": email, "token_version": token_version}
        for key in exclude or set():
            data.pop(key, None)
        return data

    return type(
        "UserStub",
        (),
        {
            "id": user_id,
            "email": email,
            "token_version": token_version,
            "to_dict": _to_dict,
        },
    )()


def _build_app(monkeypatch, current_user=None, authenticate_impl=None, create_access_token_impl=None):
    app = FastAPI()
    app.include_router(user_routes.router)
    monkeypatch.setattr(
        "routes.user.user_service.authenticate",
        authenticate_impl or (lambda email, password: (_make_user(email=email), object())),
    )
    monkeypatch.setattr(
        "routes.user.create_access_token",
        create_access_token_impl or (lambda data, expires_delta=None: "cookie-token"),
    )
    monkeypatch.setattr("routes.user.should_persist_auth_cookie", lambda token: False)
    if current_user is not None:
        app.dependency_overrides[user_routes.get_current_user] = lambda: current_user
    return app


def test_login_sets_session_auth_cookie_without_remember_me(monkeypatch):
    client = TestClient(_build_app(monkeypatch))

    response = client.post(
        "/api/users/login",
        json={"email": "demo@example.com", "password": "secret"},
        headers={"x-forwarded-proto": "https"},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {"id": 7, "email": "demo@example.com"}
    assert response.cookies.get(AUTH_COOKIE_NAME) == "cookie-token"
    set_cookie_header = response.headers["set-cookie"].lower()
    assert f"{AUTH_COOKIE_NAME}=cookie-token" in set_cookie_header
    assert "httponly" in set_cookie_header
    assert "secure" in set_cookie_header
    assert "samesite=lax" in set_cookie_header
    assert "max-age=" not in set_cookie_header


def test_login_sets_persistent_auth_cookie_when_remember_me_enabled(monkeypatch):
    client = TestClient(_build_app(monkeypatch))

    response = client.post(
        "/api/users/login",
        json={"email": "demo@example.com", "password": "secret", "remember_me": True},
    )

    assert response.status_code == 200
    set_cookie_header = response.headers["set-cookie"].lower()
    assert f"{AUTH_COOKIE_NAME}=cookie-token" in set_cookie_header
    assert "max-age=2592000" in set_cookie_header


def test_logout_clears_auth_cookie(monkeypatch):
    client = TestClient(_build_app(monkeypatch))

    response = client.post("/api/users/logout")

    assert response.status_code == 200
    assert response.json()["msg"] == "退出成功"
    cleared_cookie = response.headers["set-cookie"].lower()
    assert f"{AUTH_COOKIE_NAME}=" in cleared_cookie
    assert "max-age=0" in cleared_cookie or "expires=" in cleared_cookie


def test_login_embeds_current_token_version_and_remember_flag_in_cookie(monkeypatch):
    captured = {}

    def _capture_token(data, expires_delta=None):
        _ = expires_delta
        captured["data"] = data
        return "cookie-token"

    client = TestClient(_build_app(
        monkeypatch,
        authenticate_impl=lambda email, password: (_make_user(email=email, token_version=3), object()),
        create_access_token_impl=_capture_token,
    ))
    response = client.post(
        "/api/users/login",
        json={"email": "demo@example.com", "password": "secret", "remember_me": True},
    )

    assert response.status_code == 200
    assert captured["data"] == {"sub": "7", "tv": 3, "rm": True}


def test_update_password_rotates_cookie_for_current_session(monkeypatch):
    current_user = _make_user(token_version=1)
    updated_user = _make_user(token_version=2)
    captured = {}

    def _capture_token(data, expires_delta=None):
        _ = expires_delta
        captured["data"] = data
        return "rotated-token"

    monkeypatch.setattr("routes.user.user_service.update_password", lambda user_id, current_password, new_password: (updated_user, object()))

    app = _build_app(monkeypatch, current_user=current_user, create_access_token_impl=_capture_token)
    monkeypatch.setattr("routes.user.should_persist_auth_cookie", lambda token: True)
    client = TestClient(app)
    response = client.put(
        "/api/users/me/password",
        json={"current_password": "secret123", "new_password": "secret456"},
    )

    assert response.status_code == 200
    assert response.json()["msg"] == "密码修改成功，旧会话已失效"
    assert response.cookies.get(AUTH_COOKIE_NAME) == "rotated-token"
    assert captured["data"] == {"sub": "7", "tv": 2, "rm": True}
    assert "max-age=2592000" in response.headers["set-cookie"].lower()


def test_revoke_sessions_rotates_cookie_for_current_session(monkeypatch):
    current_user = _make_user(token_version=4)
    updated_user = _make_user(token_version=5)
    captured = {}

    def _capture_token(data, expires_delta=None):
        _ = expires_delta
        captured["data"] = data
        return "rotated-token"

    monkeypatch.setattr("routes.user.user_service.rotate_token_version", lambda user_id: updated_user)

    app = _build_app(monkeypatch, current_user=current_user, create_access_token_impl=_capture_token)
    monkeypatch.setattr("routes.user.should_persist_auth_cookie", lambda token: False)
    client = TestClient(app)
    response = client.post("/api/users/me/revoke-sessions")

    assert response.status_code == 200
    assert response.json()["msg"] == "已撤销其他会话"
    assert response.cookies.get(AUTH_COOKIE_NAME) == "rotated-token"
    assert captured["data"] == {"sub": "7", "tv": 5, "rm": False}
    assert "max-age=" not in response.headers["set-cookie"].lower()
