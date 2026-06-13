from __future__ import annotations

import json
import logging
import threading
import time
from datetime import date, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from crawl import (
    SiteRuntime,
    SiteRuntimeError,
    SiteRuntimeHealthStatus,
    SiteRuntimeInvokeRequest,
    SiteRuntimeInvokeResponse,
)

logger = logging.getLogger(__name__)


class BridgeServer(ThreadingHTTPServer):
    runtime: SiteRuntime


class BridgeHandler(BaseHTTPRequestHandler):
    server: BridgeServer

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, default=json_default).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get('Content-Length', '0') or '0')
        raw_body = self.rfile.read(content_length) if content_length > 0 else b'{}'
        payload = json.loads(raw_body.decode('utf-8') or '{}')
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _build_invoke_log_fields(request: SiteRuntimeInvokeRequest, *, elapsed_ms: int | None = None) -> dict[str, Any]:
        payload = dict(request.payload or {})
        fields = {
            'request_id': request.request_id,
            'task_id': payload.get('task_id'),
            'capability': request.capability,
            'site_name': request.site_name or payload.get('site_name'),
            'url': payload.get('url'),
            'timeout_ms': request.timeout_ms or payload.get('timeout_ms'),
        }
        if elapsed_ms is not None:
            fields['elapsed_ms'] = elapsed_ms
        return fields

    def _log_invoke_event(
        self,
        message: str,
        request: SiteRuntimeInvokeRequest,
        *,
        level: int,
        elapsed_ms: int | None = None,
    ) -> None:
        fields = self._build_invoke_log_fields(request, elapsed_ms=elapsed_ms)
        logger.log(
            level,
            '%s: request_id=%s, task_id=%s, capability=%s, site_name=%s, url=%s, timeout_ms=%s, elapsed_ms=%s',
            message,
            fields.get('request_id'),
            fields.get('task_id'),
            fields.get('capability'),
            fields.get('site_name'),
            fields.get('url'),
            fields.get('timeout_ms'),
            fields.get('elapsed_ms'),
        )

    def _write_invoke_response(
        self,
        request: SiteRuntimeInvokeRequest,
        response: SiteRuntimeInvokeResponse,
        *,
        elapsed_ms: int,
    ) -> None:
        try:
            self._write_json(HTTPStatus.OK, response.to_dict())
        except (ConnectionError, OSError) as exc:
            self._log_invoke_event(
                'Site runtime invoke response dropped because client disconnected',
                request,
                level=logging.WARNING,
                elapsed_ms=elapsed_ms,
            )
            logger.warning('Site runtime response write failed: %s', exc)

    def do_GET(self) -> None:
        if self.path != '/health':
            self._write_json(HTTPStatus.NOT_FOUND, {'error': 'not_found'})
            return

        health = self.server.runtime.health()
        if isinstance(health, SiteRuntimeHealthStatus):
            self._write_json(HTTPStatus.OK, health.to_dict())
            return
        self._write_json(HTTPStatus.OK, SiteRuntimeHealthStatus.from_dict(health).to_dict())

    def do_POST(self) -> None:
        if self.path == '/invoke':
            self._handle_invoke()
            return

        if self.path == '/stop':
            self._handle_stop()
            return

        self._write_json(HTTPStatus.NOT_FOUND, {'error': 'not_found'})

    def _handle_invoke(self) -> None:
        payload = self._read_json()
        request = SiteRuntimeInvokeRequest.from_dict(payload.get('request') or {})
        if request.trace_id:
            from shared_kernel.infrastructure.trace import set_trace_id
            set_trace_id(request.trace_id)
        started_at = time.monotonic()
        self._log_invoke_event('Site runtime invoke started', request, level=logging.INFO)
        response = self.server.runtime.invoke(request.capability, request.payload)
        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        self._log_invoke_event('Site runtime invoke finished', request, level=logging.INFO, elapsed_ms=elapsed_ms)
        self._write_invoke_response(request, self._normalize_response(request, response), elapsed_ms=elapsed_ms)

    def _handle_stop(self) -> None:
        self._write_json(HTTPStatus.OK, {'ok': True})

        def _shutdown() -> None:
            try:
                self.server.runtime.stop()
            finally:
                self.server.shutdown()

        threading.Thread(target=_shutdown, daemon=True).start()

    @staticmethod
    def _normalize_response(
        request: SiteRuntimeInvokeRequest,
        response,
    ) -> SiteRuntimeInvokeResponse:
        if isinstance(response, SiteRuntimeInvokeResponse):
            return response
        if isinstance(response, dict):
            return SiteRuntimeInvokeResponse.from_dict(response)
        return SiteRuntimeInvokeResponse(
            request_id=request.request_id,
            ok=False,
            error=SiteRuntimeError.bad_response(
                'Site runtime returned an unsupported response type',
                details={'capability': request.capability},
            ),
        )


def json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, 'to_dict') and callable(value.to_dict):
        return value.to_dict()
    raise TypeError(f'Object of type {type(value).__name__} is not JSON serializable')
