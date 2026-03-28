from __future__ import annotations

import argparse
from datetime import date, datetime
import importlib
import json
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from crawl import PluginHealthStatus, PluginInvokeRequest, PluginInvokeResponse, PluginRuntime, PluginRuntimeError


def _configure_backend_runtime_state() -> None:
    try:
        from utils.cloudflare_bypass import get_default_client
        from utils.cookie import resolve_cookie_file_for_url
        from utils.runtime_http import set_cloudflare_bypass_client, set_cookie_file_resolver

        set_cloudflare_bypass_client(get_default_client())
        set_cookie_file_resolver(resolve_cookie_file_for_url)
    except Exception:
        pass


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Squirrel plugin runtime bridge')
    parser.add_argument('--entrypoint', required=True)
    parser.add_argument('--plugin-id', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--data-dir')
    parser.add_argument('--granted-permission', action='append', default=[])
    parser.add_argument('--network-policy')
    parser.add_argument('--max-runtime-seconds', type=float)
    parser.add_argument('--memory-limit-mb', type=int)
    parser.add_argument('--cpu-time-limit-seconds', type=int)
    parser.add_argument('--max-open-files', type=int)
    parser.add_argument('--import-path', action='append', default=[])
    return parser.parse_args()


def _load_runtime(entrypoint: str) -> PluginRuntime:
    module_name, _, factory_name = entrypoint.partition(':')
    if not module_name or not factory_name:
        raise RuntimeError(f'Invalid runtime entrypoint: {entrypoint}')

    importlib.invalidate_caches()
    module = importlib.import_module(module_name)
    factory = getattr(module, factory_name, None)
    if factory is None:
        raise RuntimeError(f'Runtime factory not found: {entrypoint}')

    runtime = factory()
    if not isinstance(runtime, PluginRuntime):
        raise RuntimeError(f'Runtime factory did not return PluginRuntime: {entrypoint}')
    return runtime


class _BridgeServer(ThreadingHTTPServer):
    runtime: PluginRuntime


class _BridgeHandler(BaseHTTPRequestHandler):
    server: _BridgeServer

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, default=_json_default).encode('utf-8')
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

    def do_GET(self) -> None:  # noqa: N802
        if self.path != '/health':
            self._write_json(HTTPStatus.NOT_FOUND, {'error': 'not_found'})
            return

        health = self.server.runtime.health()
        if isinstance(health, PluginHealthStatus):
            self._write_json(HTTPStatus.OK, health.to_dict())
            return
        self._write_json(HTTPStatus.OK, PluginHealthStatus.from_dict(health).to_dict())

    def do_POST(self) -> None:  # noqa: N802
        if self.path == '/invoke':
            payload = self._read_json()
            request = PluginInvokeRequest.from_dict(payload.get('request') or {})
            response = self.server.runtime.invoke(request.capability, request.payload)
            if isinstance(response, PluginInvokeResponse):
                self._write_json(HTTPStatus.OK, response.to_dict())
                return
            if isinstance(response, dict):
                self._write_json(HTTPStatus.OK, PluginInvokeResponse.from_dict(response).to_dict())
                return
            self._write_json(
                HTTPStatus.OK,
                PluginInvokeResponse(
                    request_id=request.request_id,
                    ok=False,
                    error=PluginRuntimeError.bad_response(
                        'Plugin runtime returned an unsupported response type',
                        details={'capability': request.capability},
                    ),
                ).to_dict(),
            )
            return

        if self.path == '/stop':
            self._write_json(HTTPStatus.OK, {'ok': True})

            def _shutdown() -> None:
                try:
                    self.server.runtime.stop()
                finally:
                    self.server.shutdown()

            threading.Thread(target=_shutdown, daemon=True).start()
            return

        self._write_json(HTTPStatus.NOT_FOUND, {'error': 'not_found'})


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, 'to_dict') and callable(value.to_dict):
        return value.to_dict()
    raise TypeError(f'Object of type {type(value).__name__} is not JSON serializable')


def main() -> int:
    args = _parse_args()

    for import_path in args.import_path:
        if import_path and import_path not in sys.path:
            sys.path.insert(0, import_path)

    _configure_backend_runtime_state()
    runtime = _load_runtime(args.entrypoint)
    runtime.start({
        'plugin_id': args.plugin_id,
        'version': args.version,
        'data_dir': args.data_dir,
        'granted_permissions': list(args.granted_permission or []),
        'network_policy': json.loads(args.network_policy) if args.network_policy else None,
        'runtime_policy': {
            'max_runtime_seconds': args.max_runtime_seconds,
            'memory_limit_mb': args.memory_limit_mb,
            'cpu_time_limit_seconds': args.cpu_time_limit_seconds,
            'max_open_files': args.max_open_files,
        },
        'isolated': False,
    })

    server = _BridgeServer((args.host, args.port), _BridgeHandler)
    server.runtime = runtime

    try:
        server.serve_forever()
    finally:
        try:
            runtime.stop()
        except Exception:
            pass
        server.server_close()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
