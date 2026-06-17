import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infrastructure.http import response


def _build_client() -> TestClient:
    app = FastAPI()

    @app.get("/param-error")
    def param_error():
        return response.param_error("bad request")

    @app.get("/not-found")
    def not_found():
        return response.not_found("missing")

    @app.get("/server-error")
    def server_error():
        return response.server_error("failed")

    return TestClient(app)


def test_error_helpers_return_matching_http_status():
    client = _build_client()

    param_error = client.get("/param-error")
    not_found = client.get("/not-found")
    server_error = client.get("/server-error")

    assert param_error.status_code == 400
    assert param_error.json()["code"] == 400
    assert not_found.status_code == 404
    assert not_found.json()["code"] == 404
    assert server_error.status_code == 500
    assert server_error.json()["code"] == 500
