import logging
import re
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from application.middleware.access_log import AccessLogMiddleware
from application.middleware.trace import RequestContextMiddleware
from shared_kernel.infrastructure.log import TraceIdFilter
from shared_kernel.infrastructure.trace import get_trace_id


def _build_app():
    app = FastAPI()
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestContextMiddleware)

    @app.get("/api/demo")
    async def demo(request: Request):
        return JSONResponse({
            "trace_id": get_trace_id(),
            "state_trace_id": request.state.trace_id,
        })

    return app


def test_request_context_middleware_generates_and_returns_trace_id():
    client = TestClient(_build_app())

    response = client.get("/api/demo")

    trace_id = response.headers["X-Trace-Id"]
    assert re.fullmatch(r"[0-9a-f]{32}", trace_id)
    assert response.json()["trace_id"] == trace_id
    assert response.json()["state_trace_id"] == trace_id


def test_request_context_middleware_preserves_incoming_trace_id():
    client = TestClient(_build_app())

    response = client.get("/api/demo", headers={"X-Trace-Id": "trace-from-client"})

    assert response.headers["X-Trace-Id"] == "trace-from-client"
    assert response.json()["trace_id"] == "trace-from-client"
    assert response.json()["state_trace_id"] == "trace-from-client"


def test_access_log_middleware_logs_request_with_trace_id_and_sanitized_path():
    logger = logging.getLogger("squirrel.access")
    records = []

    class _CaptureHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = _CaptureHandler()
    handler.addFilter(TraceIdFilter())
    logger.addHandler(handler)
    previous_level = logger.level
    logger.setLevel(logging.INFO)

    try:
        client = TestClient(_build_app())
        response = client.get("/api/demo?secret=hidden", headers={"X-Trace-Id": "trace-log-1"})
        assert response.status_code == 200
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)

    assert records
    record = records[-1]
    assert record.trace_id == "trace-log-1"
    assert "method=GET" in record.getMessage()
    assert "path=/api/demo" in record.getMessage()
    assert "status=200" in record.getMessage()
    assert "secret=hidden" not in record.getMessage()


def test_access_log_middleware_is_not_blocked_by_uvicorn_access_logger_state():
    app_logger = logging.getLogger("squirrel.access")
    uvicorn_logger = logging.getLogger("uvicorn.access")
    records = []

    class _CaptureHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = _CaptureHandler()
    handler.addFilter(TraceIdFilter())
    app_logger.addHandler(handler)
    previous_app_level = app_logger.level
    previous_uvicorn_propagate = uvicorn_logger.propagate
    previous_uvicorn_handlers = list(uvicorn_logger.handlers)
    app_logger.setLevel(logging.INFO)
    uvicorn_logger.handlers = []
    uvicorn_logger.propagate = False

    try:
        client = TestClient(_build_app())
        response = client.get("/api/demo", headers={"X-Trace-Id": "trace-log-2"})
        assert response.status_code == 200
    finally:
        app_logger.removeHandler(handler)
        app_logger.setLevel(previous_app_level)
        uvicorn_logger.handlers = previous_uvicorn_handlers
        uvicorn_logger.propagate = previous_uvicorn_propagate

    assert records
    assert records[-1].trace_id == "trace-log-2"
