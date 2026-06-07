from __future__ import annotations

import argparse
import importlib
import json
import logging
import sys
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


def _configure_backend_runtime_state() -> None:
    try:
        from utils.cloudflare_bypass import get_default_client
        from utils.runtime_http import set_cloudflare_bypass_client

        set_cloudflare_bypass_client(get_default_client())
    except Exception:
        # process boundary -- optional runtime init, must not crash the subprocess
        pass
    try:
        from utils.cookie import resolve_cookie_file_for_url, resolve_cookie_match_domain_for_url
        from utils.runtime_http import set_cookie_domain_resolver, set_cookie_file_resolver

        set_cookie_file_resolver(resolve_cookie_file_for_url)
        set_cookie_domain_resolver(resolve_cookie_match_domain_for_url)
    except Exception:
        # process boundary -- optional runtime init, must not crash the subprocess
        pass
    try:
        from core.site_config_manager import apply_crawl_rate_limit_overrides

        apply_crawl_rate_limit_overrides()
    except Exception:
        # process boundary -- optional runtime init, must not crash the subprocess
        pass


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Squirrel site runtime bridge")
    parser.add_argument("--entrypoint", required=True)
    parser.add_argument("--runtime-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--data-dir")
    parser.add_argument("--granted-permission", action="append", default=[])
    parser.add_argument("--network-policy")
    parser.add_argument("--max-runtime-seconds", type=float)
    parser.add_argument("--import-path", action="append", default=[])
    return parser.parse_args()


def _load_runtime(entrypoint: str) -> SiteRuntime:
    module_name, _, factory_name = entrypoint.partition(":")
    if not module_name or not factory_name:
        raise RuntimeError(f"Invalid runtime entrypoint: {entrypoint}")

    importlib.invalidate_caches()
    module = importlib.import_module(module_name)
    factory = getattr(module, factory_name, None)
    if factory is None:
        raise RuntimeError(f"Runtime factory not found: {entrypoint}")

    runtime = factory()
    if not isinstance(runtime, SiteRuntime):
        raise RuntimeError(f"Runtime factory did not return SiteRuntime: {entrypoint}")
    return runtime


class _BridgeServer(ThreadingHTTPServer):
    runtime: SiteRuntime


class _BridgeHandler(BaseHTTPRequestHandler):
    server: _BridgeServer

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, default=_json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        payload = json.loads(raw_body.decode("utf-8") or "{}")
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _build_invoke_log_fields(request: SiteRuntimeInvokeRequest, *, elapsed_ms: int | None = None) -> dict[str, Any]:
        payload = dict(request.payload or {})
        fields = {
            "request_id": request.request_id,
            "task_id": payload.get("task_id"),
            "capability": request.capability,
            "site_name": request.site_name or payload.get("site_name"),
            "url": payload.get("url"),
            "timeout_ms": request.timeout_ms or payload.get("timeout_ms"),
        }
        if elapsed_ms is not None:
            fields["elapsed_ms"] = elapsed_ms
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
            "%s: request_id=%s, task_id=%s, capability=%s, site_name=%s, url=%s, timeout_ms=%s, elapsed_ms=%s",
            message,
            fields.get("request_id"),
            fields.get("task_id"),
            fields.get("capability"),
            fields.get("site_name"),
            fields.get("url"),
            fields.get("timeout_ms"),
            fields.get("elapsed_ms"),
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
                "Site runtime invoke response dropped because client disconnected",
                request,
                level=logging.WARNING,
                elapsed_ms=elapsed_ms,
            )
            logger.warning("Site runtime response write failed: %s", exc)

    def do_GET(self) -> None:
        if self.path != "/health":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        health = self.server.runtime.health()
        if isinstance(health, SiteRuntimeHealthStatus):
            self._write_json(HTTPStatus.OK, health.to_dict())
            return
        self._write_json(HTTPStatus.OK, SiteRuntimeHealthStatus.from_dict(health).to_dict())

    def do_POST(self) -> None:
        if self.path == "/invoke":
            payload = self._read_json()
            request = SiteRuntimeInvokeRequest.from_dict(payload.get("request") or {})
            started_at = time.monotonic()
            self._log_invoke_event("Site runtime invoke started", request, level=logging.INFO)
            response = self.server.runtime.invoke(request.capability, request.payload)
            elapsed_ms = int((time.monotonic() - started_at) * 1000)
            self._log_invoke_event("Site runtime invoke finished", request, level=logging.INFO, elapsed_ms=elapsed_ms)
            if isinstance(response, SiteRuntimeInvokeResponse):
                self._write_invoke_response(request, response, elapsed_ms=elapsed_ms)
                return
            if isinstance(response, dict):
                self._write_invoke_response(
                    request,
                    SiteRuntimeInvokeResponse.from_dict(response),
                    elapsed_ms=elapsed_ms,
                )
                return
            self._write_invoke_response(
                request,
                SiteRuntimeInvokeResponse(
                    request_id=request.request_id,
                    ok=False,
                    error=SiteRuntimeError.bad_response(
                        "Site runtime returned an unsupported response type",
                        details={"capability": request.capability},
                    ),
                ),
                elapsed_ms=elapsed_ms,
            )
            return

        if self.path == "/stop":
            self._write_json(HTTPStatus.OK, {"ok": True})

            def _shutdown() -> None:
                try:
                    self.server.runtime.stop()
                finally:
                    self.server.shutdown()

            threading.Thread(target=_shutdown, daemon=True).start()
            return

        self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
    args = _parse_args()

    for import_path in args.import_path:
        if import_path and import_path not in sys.path:
            sys.path.insert(0, import_path)

    _configure_backend_runtime_state()
    runtime = _load_runtime(args.entrypoint)
    runtime.start({
        "runtime_id": args.runtime_id,
        "version": args.version,
        "data_dir": args.data_dir,
        "granted_permissions": list(args.granted_permission or []),
        "network_policy": json.loads(args.network_policy) if args.network_policy else None,
        "runtime_policy": {
            "max_runtime_seconds": args.max_runtime_seconds,
        },
    })

    server = _BridgeServer((args.host, args.port), _BridgeHandler)
    server.runtime = runtime

    try:
        server.serve_forever()
    finally:
        try:
            runtime.stop()
        except Exception:
            # cleanup during shutdown -- must not propagate
            pass
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


