import asyncio
import logging
import os
from pathlib import Path
import sys
import types
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'squirrel-backend'))
sys.path.insert(0, str(ROOT / 'squirrel-sdk' / 'src'))


class _AlembicConfig:
    def __init__(self, *_args, **_kwargs):
        self.attributes = {}

    def set_main_option(self, *_args, **_kwargs):
        return None


alembic_module = types.ModuleType('alembic')
alembic_module.command = SimpleNamespace(upgrade=lambda *_args, **_kwargs: None)
alembic_config_module = types.ModuleType('alembic.config')
alembic_config_module.Config = _AlembicConfig
bs4_module = types.ModuleType('bs4')
bs4_module.BeautifulSoup = object
redis_module = types.ModuleType('redis')
redis_client_module = types.ModuleType('redis.client')


class _BlockingConnectionPool:
    def __init__(self, *_args, **_kwargs):
        pass


class _Redis:
    def __init__(self, *_args, **_kwargs):
        pass


class _RedisLock:
    def __init__(self, *_args, **_kwargs):
        pass


class _PubSubWorkerThread:
    def __init__(self, *_args, **_kwargs):
        pass


redis_module.BlockingConnectionPool = _BlockingConnectionPool
redis_module.Redis = _Redis
redis_client_module.PubSubWorkerThread = _PubSubWorkerThread
redis_module.client = redis_client_module
redis_lock_module = types.ModuleType('redis_lock')
redis_lock_module.Lock = _RedisLock
sys.modules.setdefault('alembic', alembic_module)
sys.modules.setdefault('alembic.config', alembic_config_module)
sys.modules.setdefault('bs4', bs4_module)
sys.modules.setdefault('redis', redis_module)
sys.modules.setdefault('redis.client', redis_client_module)
sys.modules.setdefault('redis_lock', redis_lock_module)

from crawl import SiteRuntimeInvokeResponse
from crawl import utils as crawl_utils
import main as app_main
from site_runtimes import runtime_bridge
from processes import service_runtime
from routes import health
from utils import runtime_http


def test_lifespan_configures_backend_runtime_http_state(monkeypatch):
    client = object()
    resolver = lambda url: f'cookie:{url}'
    domain_resolver = lambda url: 'youtube.com'
    projection_calls = []

    monkeypatch.setattr(app_main, 'apply_site_config_overrides', lambda: None)
    monkeypatch.setattr(app_main, 'bootstrap_site_runtimes', lambda: None)
    monkeypatch.setattr(app_main, 'shutdown_site_runtimes', lambda: None)
    monkeypatch.setattr(app_main, 'resolve_cookie_file_for_url', resolver)
    monkeypatch.setattr(app_main, 'resolve_cookie_match_domain_for_url', domain_resolver)
    monkeypatch.setattr('utils.cloudflare_bypass.get_default_client', lambda: client)
    monkeypatch.setitem(
        sys.modules,
        'services.video_extraction_projection_service',
        SimpleNamespace(ensure_projection_seeded=lambda: projection_calls.append('seeded') or 0),
    )
    monkeypatch.setitem(
        sys.modules,
        'services.scheduled_task_bootstrap',
        SimpleNamespace(ensure_system_tasks=lambda: None),
    )

    runtime_http.reset_runtime_http_state()

    async def _run() -> None:
        async with app_main.lifespan(SimpleNamespace()):
            assert runtime_http.get_cloudflare_bypass_client() is client
            assert crawl_utils._cookie_file_resolver is resolver
            assert crawl_utils._cookie_domain_resolver is domain_resolver

    asyncio.run(_run())
    assert projection_calls == ['seeded']


def test_lifespan_logs_ordered_startup_and_shutdown_sequence(monkeypatch, caplog):
    client = object()
    resolver = lambda url: f'cookie:{url}'
    domain_resolver = lambda url: 'youtube.com'

    monkeypatch.setattr(app_main, 'apply_site_config_overrides', lambda: None)
    monkeypatch.setattr(app_main, 'bootstrap_site_runtimes', lambda: None)
    monkeypatch.setattr(app_main, 'shutdown_site_runtimes', lambda: None)
    monkeypatch.setattr(app_main, 'resolve_cookie_file_for_url', resolver)
    monkeypatch.setattr(app_main, 'resolve_cookie_match_domain_for_url', domain_resolver)
    monkeypatch.setattr('utils.cloudflare_bypass.get_default_client', lambda: client)
    monkeypatch.setitem(
        sys.modules,
        'services.video_extraction_projection_service',
        SimpleNamespace(ensure_projection_seeded=lambda: 0),
    )
    monkeypatch.setitem(
        sys.modules,
        'services.scheduled_task_bootstrap',
        SimpleNamespace(ensure_system_tasks=lambda: None),
    )

    runtime_http.reset_runtime_http_state()

    async def _run() -> None:
        async with app_main.lifespan(SimpleNamespace()):
            pass

    with caplog.at_level(logging.INFO, logger='main'):
        asyncio.run(_run())

    messages = [record.getMessage() for record in caplog.records if record.name == 'main']
    assert messages == [
        'Startup: begin',
        'Startup [1/5] Applying site configuration overrides',
        'Startup [1/5] Site configuration overrides applied',
        'Startup [2/5] Configuring runtime HTTP helpers',
        'Startup [2/5] Runtime HTTP helpers ready',
        'Startup [3/5] Bootstrapping site runtime manager',
        'Startup [3/5] Site runtime manager ready',
        'Startup [4/5] Seeding video extraction projection',
        'Startup [4/5] Video extraction projection ready (rebuilt=0)',
        'Startup [5/5] Bootstrapping scheduled tasks',
        'Startup [5/5] Scheduled tasks ready',
        'Startup: complete',
        'Shutdown: begin',
        'Shutdown [1/1] Stopping site runtime manager',
        'Shutdown [1/1] Site runtime manager stopped',
        'Shutdown: complete',
    ]


def test_lifespan_sets_youtube_oauth_env_before_bootstrap(monkeypatch):
    captured = {}

    monkeypatch.setattr(app_main, 'apply_site_config_overrides', lambda: None)
    monkeypatch.setattr(app_main, 'shutdown_site_runtimes', lambda: None)
    monkeypatch.setattr('utils.cloudflare_bypass.get_default_client', lambda: object())
    monkeypatch.setattr(app_main, 'resolve_cookie_file_for_url', lambda url: url)
    monkeypatch.setattr(app_main, 'resolve_cookie_match_domain_for_url', lambda _url: 'youtube.com')
    monkeypatch.setitem(
        sys.modules,
        'services.video_extraction_projection_service',
        SimpleNamespace(ensure_projection_seeded=lambda: 0),
    )
    monkeypatch.setitem(
        sys.modules,
        'services.scheduled_task_bootstrap',
        SimpleNamespace(ensure_system_tasks=lambda: None),
    )
    monkeypatch.setitem(
        sys.modules,
        'services.youtube_oauth_service',
        SimpleNamespace(get_oauth_credentials_for_daemon=lambda: 'D:/tmp/youtube_oauth.json'),
    )

    def _capture_bootstrap():
        captured['oauth_env'] = os.environ.get('YOUTUBE_OAUTH_STATE_FILE')

    monkeypatch.setattr(app_main, 'bootstrap_site_runtimes', _capture_bootstrap)
    monkeypatch.delenv('YOUTUBE_OAUTH_STATE_FILE', raising=False)

    async def _run() -> None:
        async with app_main.lifespan(SimpleNamespace()):
            pass

    asyncio.run(_run())
    assert captured['oauth_env'] == 'D:/tmp/youtube_oauth.json'


def test_lifespan_fails_when_site_config_overrides_fail(monkeypatch):
    def _raise_site_config_error():
        raise RuntimeError('invalid site config')

    monkeypatch.setattr(app_main, 'apply_site_config_overrides', _raise_site_config_error)

    async def _run() -> None:
        async with app_main.lifespan(SimpleNamespace()):
            pass

    try:
        asyncio.run(_run())
    except RuntimeError as exc:
        assert str(exc) == 'invalid site config'
    else:
        raise AssertionError('Expected lifespan to fail on site config errors')


def test_lifespan_records_optional_scheduled_task_degradation(monkeypatch):
    from core.startup_dependencies import list_optional_startup_issues

    def _raise_scheduled_task_error():
        raise RuntimeError('scheduler table missing')

    monkeypatch.setattr(app_main, 'apply_site_config_overrides', lambda: None)
    monkeypatch.setattr(app_main, 'bootstrap_site_runtimes', lambda: None)
    monkeypatch.setattr(app_main, 'shutdown_site_runtimes', lambda: None)
    monkeypatch.setattr('utils.cloudflare_bypass.get_default_client', lambda: object())
    monkeypatch.setattr(app_main, 'resolve_cookie_file_for_url', lambda url: url)
    monkeypatch.setattr(app_main, 'resolve_cookie_match_domain_for_url', lambda _url: 'youtube.com')
    monkeypatch.setitem(
        sys.modules,
        'services.video_extraction_projection_service',
        SimpleNamespace(ensure_projection_seeded=lambda: 0),
    )
    monkeypatch.setitem(
        sys.modules,
        'services.scheduled_task_bootstrap',
        SimpleNamespace(ensure_system_tasks=_raise_scheduled_task_error),
    )

    async def _run() -> None:
        async with app_main.lifespan(SimpleNamespace()):
            issues = list_optional_startup_issues()
            assert [(issue.name, issue.error) for issue in issues] == [
                ('scheduled_task_bootstrap', 'scheduler table missing'),
            ]

    asyncio.run(_run())


def test_health_reports_optional_startup_degradation(monkeypatch):
    from core.startup_dependencies import record_optional_startup_issue, reset_startup_dependency_issues

    class _Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def execute(self, _statement):
            return None

    class _Engine:
        def connect(self):
            return _Connection()

    class _RedisClient:
        def ping(self):
            return True

    reset_startup_dependency_issues()
    record_optional_startup_issue('cloudflare_bypass', RuntimeError('service unavailable'))
    monkeypatch.setattr(health, 'engine', _Engine())
    monkeypatch.setattr(health, 'redis_client', _RedisClient())

    result = asyncio.run(health.health_check())

    assert result['status'] == 'degraded'
    assert result['checks']['startup_optional'] == 'degraded'
    assert result['startup_optional_issues'] == [
        {'name': 'cloudflare_bypass', 'error': 'service unavailable'},
    ]
    reset_startup_dependency_issues()


def test_bootstrap_runtime_configures_backend_runtime_http_state(monkeypatch):
    client = object()
    resolver = lambda url: f'cookie:{url}'
    domain_resolver = lambda url: 'youtube.com'
    projection_calls = []

    monkeypatch.setattr(service_runtime, 'init_logging', lambda: None)
    monkeypatch.setattr(service_runtime, 'upgrade_database', lambda: None)
    monkeypatch.setattr(service_runtime, 'apply_site_config_overrides', lambda: None)
    monkeypatch.setattr(service_runtime, 'bootstrap_site_runtimes', lambda: None)
    monkeypatch.setattr(service_runtime, 'shutdown_site_runtimes', lambda: None)
    monkeypatch.setattr(service_runtime, 'start_reload_listener', lambda component: None)
    monkeypatch.setattr(service_runtime, 'stop_reload_listener', lambda component: None)
    monkeypatch.setitem(
        sys.modules,
        'services.subscription_sync_state_service',
        SimpleNamespace(
            recover_stale_queued_sync_states=lambda: {'recovered': 0},
            recover_stale_running_sync_states=lambda: {'recovered': 0},
            reconcile_terminal_drained_sync_states=lambda: {'completed': 0, 'failed': 0},
            reconcile_retry_wait_run_projections=lambda: {'repaired': 0},
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        'services.video_extraction_projection_service',
        SimpleNamespace(ensure_projection_seeded=lambda: projection_calls.append('seeded') or 0),
    )
    monkeypatch.setattr(service_runtime, 'resolve_cookie_file_for_url', resolver)
    monkeypatch.setattr(service_runtime, 'resolve_cookie_match_domain_for_url', domain_resolver)
    monkeypatch.setattr('utils.cloudflare_bypass.get_default_client', lambda: client)

    runtime_http.reset_runtime_http_state()

    with service_runtime.bootstrap_runtime('worker'):
        assert runtime_http.get_cloudflare_bypass_client() is client
        assert crawl_utils._cookie_file_resolver is resolver
        assert crawl_utils._cookie_domain_resolver is domain_resolver
    assert projection_calls == ['seeded']


def test_bootstrap_runtime_sets_youtube_oauth_env_before_bootstrap(monkeypatch):
    projection_calls = []
    captured = {}

    monkeypatch.setattr(service_runtime, 'init_logging', lambda: None)
    monkeypatch.setattr(service_runtime, 'upgrade_database', lambda: None)
    monkeypatch.setattr(service_runtime, 'apply_site_config_overrides', lambda: None)
    monkeypatch.setattr(service_runtime, 'shutdown_site_runtimes', lambda: None)
    monkeypatch.setattr(service_runtime, 'start_reload_listener', lambda component: None)
    monkeypatch.setattr(service_runtime, 'stop_reload_listener', lambda component: None)
    monkeypatch.setattr('utils.cloudflare_bypass.get_default_client', lambda: object())
    monkeypatch.setattr(service_runtime, 'resolve_cookie_file_for_url', lambda url: url)
    monkeypatch.setattr(service_runtime, 'resolve_cookie_match_domain_for_url', lambda _url: 'youtube.com')
    monkeypatch.setitem(
        sys.modules,
        'services.subscription_sync_state_service',
        SimpleNamespace(
            recover_stale_queued_sync_states=lambda: {'recovered': 0},
            recover_stale_running_sync_states=lambda: {'recovered': 0},
            reconcile_terminal_drained_sync_states=lambda: {'completed': 0, 'failed': 0},
            reconcile_retry_wait_run_projections=lambda: {'repaired': 0},
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        'services.video_extraction_projection_service',
        SimpleNamespace(ensure_projection_seeded=lambda: projection_calls.append('seeded') or 0),
    )
    monkeypatch.setitem(
        sys.modules,
        'services.youtube_oauth_service',
        SimpleNamespace(get_oauth_credentials_for_daemon=lambda: 'D:/tmp/youtube_oauth.json'),
    )

    def _capture_bootstrap():
        captured['oauth_env'] = os.environ.get('YOUTUBE_OAUTH_STATE_FILE')

    monkeypatch.setattr(service_runtime, 'bootstrap_site_runtimes', _capture_bootstrap)
    monkeypatch.delenv('YOUTUBE_OAUTH_STATE_FILE', raising=False)

    with service_runtime.bootstrap_runtime('worker'):
        pass

    assert projection_calls == ['seeded']
    assert captured['oauth_env'] == 'D:/tmp/youtube_oauth.json'


def test_runtime_bridge_configures_backend_runtime_http_state(monkeypatch):
    client = object()
    resolver = lambda url: f'cookie:{url}'
    domain_resolver = lambda url: 'youtube.com'

    monkeypatch.setattr('utils.cloudflare_bypass.get_default_client', lambda: client)
    monkeypatch.setattr('utils.cookie.resolve_cookie_file_for_url', resolver)
    monkeypatch.setattr('utils.cookie.resolve_cookie_match_domain_for_url', domain_resolver)

    runtime_http.reset_runtime_http_state()
    runtime_bridge._configure_backend_runtime_state()

    assert runtime_http.get_cloudflare_bypass_client() is client
    assert crawl_utils._cookie_file_resolver is resolver
    assert crawl_utils._cookie_domain_resolver is domain_resolver


def test_runtime_bridge_keeps_cookie_resolver_when_cloudflare_bypass_is_unavailable(monkeypatch):
    resolver = lambda url: f'cookie:{url}'
    domain_resolver = lambda url: 'youtube.com'

    def _raise_missing_bypass():
        raise ValueError('missing cloudflare bypass service')

    monkeypatch.setattr('utils.cloudflare_bypass.get_default_client', _raise_missing_bypass)
    monkeypatch.setattr('utils.cookie.resolve_cookie_file_for_url', resolver)
    monkeypatch.setattr('utils.cookie.resolve_cookie_match_domain_for_url', domain_resolver)

    runtime_http.reset_runtime_http_state()
    runtime_bridge._configure_backend_runtime_state()

    assert runtime_http.get_cloudflare_bypass_client() is None
    assert crawl_utils._cookie_file_resolver is resolver
    assert crawl_utils._cookie_domain_resolver is domain_resolver


def test_runtime_bridge_syncs_site_rate_limits_into_site_runtime(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        'utils.cloudflare_bypass.get_default_client',
        lambda: object(),
    )
    monkeypatch.setattr('utils.cookie.resolve_cookie_file_for_url', lambda url: url)
    monkeypatch.setattr('utils.cookie.resolve_cookie_match_domain_for_url', lambda url: 'javdb.com')
    monkeypatch.setattr(
        'core.site_config_manager.apply_crawl_rate_limit_overrides',
        lambda catalog=None: calls.append('sdk-rate-limit'),
        raising=False,
    )

    runtime_http.reset_runtime_http_state()
    runtime_bridge._configure_backend_runtime_state()

    assert calls == ['sdk-rate-limit']


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
            return SiteRuntimeInvokeResponse(request_id='req-1', ok=True, data={'success': True})

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

    with caplog.at_level(logging.WARNING, logger='site_runtimes.runtime_bridge'):
        handler.do_POST()

    assert 'Site runtime invoke response dropped because client disconnected' in caplog.text
    assert 'request_id=req-1' in caplog.text
    assert 'capability=extract_video' in caplog.text
    assert 'url=https://www.youtube.com/watch?v=demo' in caplog.text



