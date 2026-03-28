import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main as app_main
from processes import service_runtime
from utils import runtime_http


def test_lifespan_configures_backend_runtime_http_state(monkeypatch):
    client = object()

    monkeypatch.setattr(app_main, 'apply_site_config_overrides', lambda: None)
    monkeypatch.setattr(app_main, 'bootstrap_plugin_runtime', lambda: None)
    monkeypatch.setattr(app_main, 'shutdown_plugin_runtime', lambda: None)
    monkeypatch.setitem(
        sys.modules,
        'queues.queue_config',
        SimpleNamespace(ensure_queue_config_initialized=lambda: None),
    )
    monkeypatch.setattr('utils.cloudflare_bypass.get_default_client', lambda: client)

    runtime_http.reset_runtime_http_state()

    async def _run() -> None:
        async with app_main.lifespan(SimpleNamespace()):
            assert runtime_http.get_cloudflare_bypass_client() is client

    asyncio.run(_run())


def test_bootstrap_runtime_configures_backend_runtime_http_state(monkeypatch):
    client = object()

    monkeypatch.setattr(service_runtime, 'init_logging', lambda: None)
    monkeypatch.setattr(service_runtime, 'upgrade_database', lambda: None)
    monkeypatch.setattr(service_runtime, 'apply_site_config_overrides', lambda: None)
    monkeypatch.setattr(service_runtime, 'bootstrap_plugin_runtime', lambda: None)
    monkeypatch.setattr(service_runtime, 'shutdown_plugin_runtime', lambda: None)
    monkeypatch.setattr(service_runtime, 'ensure_queue_config_initialized', lambda: None)
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
    monkeypatch.setattr('utils.cloudflare_bypass.get_default_client', lambda: client)

    runtime_http.reset_runtime_http_state()

    with service_runtime.bootstrap_runtime('worker'):
        assert runtime_http.get_cloudflare_bypass_client() is client
