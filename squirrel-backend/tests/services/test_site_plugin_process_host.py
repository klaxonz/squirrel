import json
from pathlib import Path
from queue import Empty
from types import SimpleNamespace

import pytest

import infrastructure.site_plugins.registry as registry_module
from infrastructure.site_plugins.registry import (
    SitePluginRegistry,
    _PluginProcessHost,
    _serialize_plugin_exception,
)


class _FakeQueue:
    def __init__(self, messages=None, on_empty=None):
        self.messages = list(messages or [])
        self.on_empty = on_empty
        self.sent = []

    def put(self, value):
        self.sent.append(value)

    def get(self, timeout=None):
        if self.messages:
            return self.messages.pop(0)
        if self.on_empty is not None:
            self.on_empty()
        raise Empty

    def close(self):
        return None

    def join_thread(self):
        return None


class _FakeProcess:
    def __init__(self):
        self.alive = False
        self.terminated = False

    def start(self):
        self.alive = True

    def is_alive(self):
        return self.alive

    def terminate(self):
        self.terminated = True
        self.alive = False

    def join(self, timeout=None):
        return None


class _FakeContext:
    def __init__(self):
        self.requests = _FakeQueue()
        self.responses = _FakeQueue([{'type': 'ready'}])
        self.process = _FakeProcess()
        self.queue_count = 0

    def Queue(self):
        self.queue_count += 1
        return self.requests if self.queue_count == 1 else self.responses

    def Process(self, **kwargs):
        return self.process


class _AdvancingClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class _AdvancingLock:
    def __init__(self, clock, wait_seconds):
        self.clock = clock
        self.wait_seconds = wait_seconds

    def acquire(self, timeout=None):
        self.clock.advance(min(self.wait_seconds, timeout))
        return self.wait_seconds <= timeout

    def release(self):
        return None


class _TimedQueue(_FakeQueue):
    def __init__(self, clock, messages=None, delays=None):
        super().__init__(messages=messages)
        self.clock = clock
        self.delays = list(delays or [])
        self.timeouts = []

    def get(self, timeout=None):
        timeout = float(timeout or 0.0)
        self.timeouts.append(timeout)
        if self.messages:
            delay = self.delays[0]
            elapsed = min(delay, timeout)
            self.clock.advance(elapsed)
            self.delays[0] -= elapsed
            if self.delays[0] <= 0:
                self.delays.pop(0)
                return self.messages.pop(0)
            raise Empty
        self.clock.advance(timeout)
        raise Empty


def test_plugin_timeout_terminates_isolated_process():
    context = _FakeContext()
    host = _PluginProcessHost(Path('.'), 'youtube')
    host._context = context

    response = host.invoke('extract_video', {}, timeout_seconds=0.01)

    assert response['ok'] is False
    assert response['retryable'] is True
    assert response['error']['code'] == 'PLUGIN_TIMEOUT'
    assert response['error']['details']['phase'] == 'invoke'
    assert context.process.terminated is True


def test_invoke_uses_one_deadline_for_lock_startup_and_capability(monkeypatch):
    clock = _AdvancingClock()
    context = _FakeContext()
    context.responses = _TimedQueue(clock, messages=[{'type': 'ready'}], delays=[0.4])
    host = _PluginProcessHost(Path('.'), 'youtube')
    host._context = context
    host._lock = _AdvancingLock(clock, wait_seconds=0.35)
    monkeypatch.setattr(registry_module, 'monotonic', clock)

    response = host.invoke('extract_video', {}, timeout_seconds=1.0)

    assert response['error']['code'] == 'PLUGIN_TIMEOUT'
    assert response['error']['details'] == {'phase': 'invoke', 'timeout_ms': 1000}
    assert clock.value == pytest.approx(1.0)
    assert context.responses.timeouts[-1] == pytest.approx(0.25)


def test_plugin_process_exit_is_detected_without_waiting_for_full_timeout():
    context = _FakeContext()
    context.responses.on_empty = lambda: setattr(context.process, 'alive', False)
    host = _PluginProcessHost(Path('.'), 'youtube')
    host._context = context

    response = host.invoke('extract_video', {}, timeout_seconds=30)

    assert response['ok'] is False
    assert response['retryable'] is True
    assert response['error']['code'] == 'PLUGIN_CRASHED'


def test_capability_queue_failure_is_returned_as_process_crash():
    context = _FakeContext()
    context.responses.on_empty = lambda: (_ for _ in ()).throw(EOFError('queue closed'))
    host = _PluginProcessHost(Path('.'), 'youtube')
    host._context = context

    response = host.invoke('extract_video', {}, timeout_seconds=1)

    assert response['error']['code'] == 'PLUGIN_CRASHED'
    assert response['error']['details'] == {'phase': 'invoke', 'exception_type': 'EOFError'}


def test_process_start_failure_is_returned_as_a_stable_plugin_error():
    context = _FakeContext()
    context.Process = lambda **_kwargs: (_ for _ in ()).throw(OSError('spawn failed'))
    host = _PluginProcessHost(Path('.'), 'youtube')
    host._context = context

    response = host.invoke('extract_video', {}, timeout_seconds=1)

    assert response['error']['code'] == 'PLUGIN_CRASHED'
    assert response['error']['details']['phase'] == 'startup'
    assert response['error']['details']['exception_type'] == 'OSError'


def test_startup_queue_failure_is_returned_as_process_crash():
    context = _FakeContext()
    context.responses.messages.clear()
    context.responses.on_empty = lambda: (_ for _ in ()).throw(EOFError('queue closed'))
    host = _PluginProcessHost(Path('.'), 'youtube')
    host._context = context

    response = host.invoke('extract_video', {}, timeout_seconds=1)

    assert response['error']['code'] == 'PLUGIN_CRASHED'
    assert response['error']['details']['phase'] == 'startup'
    assert response['error']['details']['exception_type'] == 'EOFError'


def test_live_host_restarts_before_use_when_its_site_config_revision_changes():
    context = _FakeContext()
    previous_process = _FakeProcess()
    previous_process.start()
    host = _PluginProcessHost(Path('.'), 'youtube')
    host._context = context
    host._process = previous_process
    host._requests = _FakeQueue()
    host._responses = _FakeQueue()
    host._config_revision = 'old-revision'
    host._read_site_config_revision = lambda: 'new-revision'

    host._ensure_started()

    assert previous_process.terminated is True
    assert context.process.alive is True
    assert host._config_revision == 'new-revision'


def test_site_config_revision_ignores_updates_for_other_sites(tmp_path):
    config_dir = tmp_path / 'config'
    config_dir.mkdir()
    config_path = config_dir / 'sites.json'
    config_path.write_text(
        json.dumps({'youtube': {'proxy': {'read_timeout': 30}}, 'bilibili': {'enabled': True}}),
        encoding='utf-8',
    )
    host = _PluginProcessHost(tmp_path, 'youtube')
    original_revision = host._read_site_config_revision()

    config_path.write_text(
        json.dumps({'youtube': {'proxy': {'read_timeout': 30}}, 'bilibili': {'enabled': False}}),
        encoding='utf-8',
    )
    assert host._read_site_config_revision() == original_revision

    config_path.write_text(
        json.dumps({'youtube': {'proxy': {'read_timeout': 60}}, 'bilibili': {'enabled': False}}),
        encoding='utf-8',
    )
    assert host._read_site_config_revision() != original_revision


def test_plugin_startup_failure_preserves_child_error_code():
    context = _FakeContext()
    context.responses.messages = [
        {
            'type': 'startup_error',
            'error': {
                'code': 'PLUGIN_AUTH_REQUIRED',
                'message': 'login required',
                'details': {'site': 'youtube'},
                'retryable': False,
            },
        },
    ]
    host = _PluginProcessHost(Path('.'), 'youtube')
    host._context = context

    response = host.invoke('import_subscriptions', {}, timeout_seconds=1)

    assert response['ok'] is False
    assert response['retryable'] is False
    assert response['error']['code'] == 'PLUGIN_AUTH_REQUIRED'
    assert response['error']['details']['phase'] == 'startup'
    assert response['error']['details']['site'] == 'youtube'


def test_process_boundary_preserves_classified_exception_code_and_retry_metadata():
    class _ClassifiedPluginError(Exception):
        retryable = True
        error_type = 'PLUGIN_NETWORK_ERROR'
        retry_after_seconds = 17

        def __init__(self, message):
            super().__init__(message)
            self.details = {'upstream': 'youtube'}

    response = _serialize_plugin_exception(_ClassifiedPluginError('temporary upstream failure'))

    assert response == {
        'ok': False,
        'data': None,
        'error': {
            'code': 'PLUGIN_NETWORK_ERROR',
            'message': 'temporary upstream failure',
            'details': {
                'upstream': 'youtube',
                'exception_type': '_ClassifiedPluginError',
                'retry_after_seconds': 17,
            },
            'retryable': True,
        },
        'retryable': True,
    }


def test_registry_keeps_runtime_error_code_after_process_deserialization():
    registry = SitePluginRegistry(repo_root=Path('.'))
    registry._plugins['youtube'] = SimpleNamespace(
        manifest=lambda: SimpleNamespace(
            capabilities=[SimpleNamespace(name='import_subscriptions', timeout_ms=1000)],
            sites=[],
        ),
    )
    registry._process_hosts['youtube'] = SimpleNamespace(
        invoke=lambda *_args: {
            'ok': False,
            'data': None,
            'error': {
                'code': 'PLUGIN_AUTH_REQUIRED',
                'message': 'login required',
                'details': {'login_url': 'https://example.com/login'},
                'retryable': False,
            },
            'retryable': False,
        },
    )
    registry.has_capability = lambda site_name, capability: True

    result = registry.invoke('import_subscriptions', site_name='youtube')

    assert result.ok is False
    assert result.error is not None
    assert result.error.code == 'PLUGIN_AUTH_REQUIRED'
    assert result.error.details == {
        'login_url': 'https://example.com/login',
        'code': 'PLUGIN_AUTH_REQUIRED',
    }


def test_registry_uses_capability_manifest_timeout():
    captured = []
    registry = SitePluginRegistry(repo_root=Path('.'))
    registry._plugins['youtube'] = SimpleNamespace(
        manifest=lambda: SimpleNamespace(
            capabilities=[SimpleNamespace(name='extract_video', timeout_ms=1250)],
            sites=[],
        ),
    )
    registry._process_hosts['youtube'] = SimpleNamespace(
        invoke=lambda capability, payload, timeout: (
            captured.append((capability, payload, timeout)) or {'ok': True, 'data': {'id': 'ok'}}
        ),
    )
    registry.has_capability = lambda site_name, capability: True

    result = registry.invoke('extract_video', site_name='youtube', payload={'url': 'https://example.com'})

    assert result.ok is True
    assert captured == [('extract_video', {'url': 'https://example.com'}, 1.25)]


def test_registry_stop_all_attempts_every_process_host():
    stopped = []
    registry = SitePluginRegistry(repo_root=Path('.'))
    registry._process_hosts = {
        'youtube': SimpleNamespace(
            stop=lambda: stopped.append('youtube') or (_ for _ in ()).throw(RuntimeError('stop failed')),
        ),
        'bilibili': SimpleNamespace(stop=lambda: stopped.append('bilibili')),
    }

    try:
        registry.stop_all()
    except RuntimeError as exc:
        assert str(exc) == 'stop failed'
    else:
        raise AssertionError('Expected stop_all to report the cleanup failure')

    assert stopped == ['youtube', 'bilibili']
    assert registry._process_hosts == {}


def test_registry_refreshes_only_active_hosts_for_changed_sites():
    restarted = []
    registry = SitePluginRegistry(repo_root=Path('.'))
    registry._process_hosts = {
        'youtube': SimpleNamespace(restart=lambda: restarted.append('youtube')),
        'bilibili': SimpleNamespace(restart=lambda: restarted.append('bilibili')),
    }

    registry.refresh_sites({'YouTube', 'unknown'})

    assert restarted == ['youtube']
