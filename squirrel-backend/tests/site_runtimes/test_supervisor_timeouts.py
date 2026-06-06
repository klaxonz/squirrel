from pathlib import Path
import socket
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crawl import SiteRuntimeInvokeRequest
from crawl.runtime_errors import RuntimeErrorCode
from site_runtimes.models import (
    SiteRuntimeHealthSnapshot,
    SiteRuntimeRecord,
    SiteRuntimeTarget,
    SiteRuntimeHandle,
    SiteRuntimeState,
)
from site_runtimes.supervisor import SiteRuntimeSupervisor


def test_supervisor_returns_timeout_error_when_runtime_request_times_out(monkeypatch):
    supervisor = SiteRuntimeSupervisor()
    supervisor._handles['javdb:0.1.0'] = SiteRuntimeHandle(
        runtime_id='javdb',
        version='0.1.0',
        state=SiteRuntimeState.RUNNING,
        endpoint='http://127.0.0.1:65535',
        health=SiteRuntimeHealthSnapshot(runtime_id='javdb', healthy=True, status='running'),
    )

    def _raise_timeout(*_args, **_kwargs):
        raise socket.timeout('timed out')

    monkeypatch.setattr(supervisor, '_request_json', _raise_timeout)

    response = supervisor.invoke(
        SiteRuntimeTarget(
            runtime_id='javdb',
            version='0.1.0',
            capability='check_login_status',
            site_name='javdb',
        ),
        SiteRuntimeInvokeRequest(
            request_id='req-1',
            capability='check_login_status',
            payload={},
            site_name='javdb',
            timeout_ms=30000,
        ),
    )

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == RuntimeErrorCode.TIMEOUT


def test_supervisor_records_timeout_invoke_context_in_audit_and_response(monkeypatch, tmp_path):
    supervisor = SiteRuntimeSupervisor()
    supervisor._handles['youtube:0.1.0'] = SiteRuntimeHandle(
        runtime_id='youtube',
        version='0.1.0',
        state=SiteRuntimeState.RUNNING,
        endpoint='http://127.0.0.1:55141',
        process_id=15120,
        health=SiteRuntimeHealthSnapshot(runtime_id='youtube', healthy=True, status='running'),
    )
    supervisor._records['youtube:0.1.0'] = SiteRuntimeRecord(
        runtime_id='youtube',
        version='0.1.0',
        install_path=str(tmp_path / 'youtube'),
        runtime_path=str(tmp_path / 'youtube'),
        entrypoint='squirrel_youtube.runtime:get_site_runtime',
        enabled=True,
        manifest={},
    )
    audit_events = []
    monotonic_values = iter([100.0, 220.125])

    monkeypatch.setattr('site_runtimes.supervisor.time.monotonic', lambda: next(monotonic_values))
    monkeypatch.setattr(
        supervisor,
        '_append_audit_event',
        lambda _record, event, details=None: audit_events.append((event, details)),
    )

    def _raise_timeout(*_args, **_kwargs):
        raise socket.timeout('timed out')

    monkeypatch.setattr(supervisor, '_request_json', _raise_timeout)

    response = supervisor.invoke(
        SiteRuntimeTarget(
            runtime_id='youtube',
            version='0.1.0',
            capability='extract_video',
            site_name='youtube',
            domain='youtube.com',
        ),
        SiteRuntimeInvokeRequest(
            request_id='req-1',
            capability='extract_video',
            payload={
                'url': 'https://www.youtube.com/watch?v=demo',
                'task_id': 'task-1',
            },
            site_name='youtube',
            timeout_ms=120000,
            metadata={'domain': 'youtube.com'},
        ),
    )

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == RuntimeErrorCode.TIMEOUT
    assert response.error.details['request_id'] == 'req-1'
    assert response.error.details['task_id'] == 'task-1'
    assert response.error.details['url'] == 'https://www.youtube.com/watch?v=demo'
    assert response.error.details['site_name'] == 'youtube'
    assert response.error.details['domain'] == 'youtube.com'
    assert response.error.details['timeout_ms'] == 120000
    assert response.error.details['elapsed_ms'] == 120125
    assert response.error.details['endpoint'] == 'http://127.0.0.1:55141'
    assert response.error.details['process_id'] == 15120
    assert ('invoke_failed', {
        'request_id': 'req-1',
        'task_id': 'task-1',
        'runtime_id': 'youtube',
        'version': '0.1.0',
        'capability': 'extract_video',
        'site_name': 'youtube',
        'domain': 'youtube.com',
        'url': 'https://www.youtube.com/watch?v=demo',
        'timeout_ms': 120000,
        'endpoint': 'http://127.0.0.1:55141',
        'process_id': 15120,
        'elapsed_ms': 120125,
        'reason': 'timed out',
    }) in audit_events


