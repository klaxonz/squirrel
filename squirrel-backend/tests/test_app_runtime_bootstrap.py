import asyncio
import logging
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crawl import PluginInvokeResponse
import main as app_main
from plugins import runtime_bridge
from processes import service_runtime
from utils import runtime_http


def test_lifespan_configures_backend_runtime_http_state(monkeypatch):
    client = object()
    resolver = lambda url: f'cookie:{url}'

    monkeypatch.setattr(app_main, 'apply_site_config_overrides', lambda: None)
    monkeypatch.setattr(app_main, 'bootstrap_plugin_runtime', lambda: None)
    monkeypatch.setattr(app_main, 'shutdown_plugin_runtime', lambda: None)
    monkeypatch.setattr(app_main, 'resolve_cookie_file_for_url', resolver)
    monkeypatch.setattr('utils.cloudflare_bypass.get_default_client', lambda: client)

    runtime_http.reset_runtime_http_state()

    async def _run() -> None:
        async with app_main.lifespan(SimpleNamespace()):
            assert runtime_http.get_cloudflare_bypass_client() is client
            assert runtime_http.get_cookie_file_resolver() is resolver

    asyncio.run(_run())


def test_bootstrap_runtime_configures_backend_runtime_http_state(monkeypatch):
    client = object()
    resolver = lambda url: f'cookie:{url}'

    monkeypatch.setattr(service_runtime, 'init_logging', lambda: None)
    monkeypatch.setattr(service_runtime, 'upgrade_database', lambda: None)
    monkeypatch.setattr(service_runtime, 'apply_site_config_overrides', lambda: None)
    monkeypatch.setattr(service_runtime, 'bootstrap_plugin_runtime', lambda: None)
    monkeypatch.setattr(service_runtime, 'shutdown_plugin_runtime', lambda: None)
    monkeypatch.setattr(service_runtime, 'start_reload_listener', lambda component: None)
    monkeypatch.setattr(service_runtime, 'stop_reload_listener', lambda component: None)
    monkeypatch.setitem(
        sys.modules,
        'services.subscription_sync_state_service',
        SimpleNamespace(
            recover_stale_queued_sync_states=lambda: {'recovered': 0},
            recover_stale_running_sync_states=lambda: {'recovered': 0},
        ),
    )
    monkeypatch.setattr(service_runtime, 'resolve_cookie_file_for_url', resolver)
    monkeypatch.setattr('utils.cloudflare_bypass.get_default_client', lambda: client)

    runtime_http.reset_runtime_http_state()

    with service_runtime.bootstrap_runtime('worker'):
        assert runtime_http.get_cloudflare_bypass_client() is client
        assert runtime_http.get_cookie_file_resolver() is resolver


def test_runtime_bridge_configures_backend_runtime_http_state(monkeypatch):
    client = object()
    resolver = lambda url: f'cookie:{url}'

    monkeypatch.setattr('utils.cloudflare_bypass.get_default_client', lambda: client)
    monkeypatch.setattr('utils.cookie.resolve_cookie_file_for_url', resolver)

    runtime_http.reset_runtime_http_state()
    runtime_bridge._configure_backend_runtime_state()

    assert runtime_http.get_cloudflare_bypass_client() is client
    assert runtime_http.get_cookie_file_resolver() is resolver


def test_runtime_bridge_logs_client_disconnect_without_traceback(monkeypatch, caplog):
    class _Runtime:
        def invoke(self, capability, payload=None):
            assert capability == 'extract_video'
            assert payload == {
                'request_id': 'req-1',
                'url': 'https://www.youtube.com/watch?v=demo',
                'task_id': 'task-1',
                'site_name': 'youtube',
                'timeout_ms': 120000,
            }
            return PluginInvokeResponse(request_id='req-1', ok=True, data={'success': True})

    handler = object.__new__(runtime_bridge._BridgeHandler)
    handler.path = '/invoke'
    handler.client_address = ('127.0.0.1', 12345)
    handler.server = SimpleNamespace(runtime=_Runtime())
    monkeypatch.setattr(
        handler,
        '_read_json',
        lambda: {
            'request': {
                'request_id': 'req-1',
                'capability': 'extract_video',
                'site_name': 'youtube',
                'timeout_ms': 120000,
                'payload': {
                    'request_id': 'req-1',
                    'url': 'https://www.youtube.com/watch?v=demo',
                    'task_id': 'task-1',
                    'site_name': 'youtube',
                    'timeout_ms': 120000,
                },
            }
        },
    )

    def _raise_client_disconnect(*_args, **_kwargs):
        raise ConnectionAbortedError(10053, 'connection aborted')

    monkeypatch.setattr(handler, '_write_json', _raise_client_disconnect)

    with caplog.at_level(logging.WARNING, logger='plugins.runtime_bridge'):
        handler.do_POST()

    assert 'Plugin invoke response dropped because client disconnected' in caplog.text
    assert 'request_id=req-1' in caplog.text
    assert 'capability=extract_video' in caplog.text
    assert 'url=https://www.youtube.com/watch?v=demo' in caplog.text
