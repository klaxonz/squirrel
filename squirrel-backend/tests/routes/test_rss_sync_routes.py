from contextlib import contextmanager
from threading import Lock
from types import SimpleNamespace
from typing import ClassVar

from fastapi import FastAPI
from fastapi.testclient import TestClient

from domains.rss.application.services.sync.service import RssSyncService
from domains.rss.interfaces.http.dependencies import get_rss_service
from domains.rss.interfaces.http.sync import router
from domains.user.application.services.auth import get_current_user


class FakeRssService:
    def __init__(self):
        self.calls = []
        self.sync_result = {'account_id': 11, 'feeds': 0, 'entries': 0, 'error': None}

    def sync_account(self, user_id, account_id, *, entry_limit=None):
        self.calls.append(
            {
                'method': 'sync_account',
                'user_id': user_id,
                'account_id': account_id,
                'entry_limit': entry_limit,
            }
        )
        return self.sync_result

    def start_account_sync(self, user_id, account_id, *, entry_limit=None, force_full_sync=False):
        self.calls.append(
            {
                'method': 'start_account_sync',
                'user_id': user_id,
                'account_id': account_id,
                'entry_limit': entry_limit,
                'force_full_sync': force_full_sync,
            }
        )
        return {'started': True, 'account_id': account_id}


class FakeAccountService:
    def __init__(self):
        self.account = SimpleNamespace(last_error=None)
        self.sync_lock = Lock()
        self.progress = {}

    def get_account(self, session, user_id, account_id):
        return self.account

    def sync_lock_for_account(self, account_id):
        return self.sync_lock

    def set_sync_progress(self, account_id, **values):
        self.progress.update(values)


class DeferredThread:
    created: ClassVar[list['DeferredThread']] = []

    def __init__(self, *, target, kwargs, name, daemon):
        self.target = target
        self.kwargs = kwargs
        self.name = name
        self.daemon = daemon
        self.__class__.created.append(self)

    def start(self):
        return None


class FailingThread(DeferredThread):
    def start(self):
        raise RuntimeError('thread start failed')


class FakeSession:
    def commit(self):
        return None


@contextmanager
def _session_factory():
    yield FakeSession()


def _create_real_sync_service():
    account_service = FakeAccountService()
    sync_service = RssSyncService(session_factory=_session_factory, account_service=account_service)
    return sync_service, account_service


def _create_client(fake_service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    app.dependency_overrides[get_rss_service] = lambda: fake_service
    return TestClient(app)


def test_start_rss_sync_forwards_query_model_values():
    fake_service = FakeRssService()
    client = _create_client(fake_service)

    route_response = client.post(
        '/accounts/11/sync/start',
        params={
            'entryLimit': 25,
            'forceFullSync': 'true',
        },
    )

    assert route_response.status_code == 200
    assert route_response.json()['data'] == {'started': True, 'account_id': 11}
    assert fake_service.calls == [
        {
            'method': 'start_account_sync',
            'user_id': 7,
            'account_id': 11,
            'entry_limit': 25,
            'force_full_sync': True,
        },
    ]


def test_legacy_sync_route_returns_not_found_for_missing_account():
    fake_service = FakeRssService()
    fake_service.sync_result = None
    client = _create_client(fake_service)

    route_response = client.post('/accounts/404/sync')

    assert route_response.status_code == 404
    assert route_response.json() == {
        'code': 404,
        'msg': 'RSS 账号不存在',
        'data': None,
    }
    assert fake_service.calls == [
        {
            'method': 'sync_account',
            'user_id': 7,
            'account_id': 404,
            'entry_limit': None,
        }
    ]


def test_start_rss_sync_rejects_second_start_without_acknowledging_it(monkeypatch):
    DeferredThread.created = []
    monkeypatch.setattr('domains.rss.application.services.sync.service.Thread', DeferredThread)
    sync_service, account_service = _create_real_sync_service()
    client = _create_client(sync_service)

    first_response = client.post('/accounts/11/sync/start')
    second_response = client.post('/accounts/11/sync/start')

    assert first_response.status_code == 200
    assert first_response.json()['data'] == {'started': True, 'account_id': 11}
    assert second_response.status_code == 400
    assert second_response.json() == {
        'code': 400,
        'msg': 'RSS account sync is already running',
        'data': None,
    }
    assert len(DeferredThread.created) == 1
    assert account_service.progress['running'] is True


def test_start_rss_sync_failure_does_not_return_started_acknowledgement(monkeypatch):
    FailingThread.created = []
    monkeypatch.setattr('domains.rss.application.services.sync.service.Thread', FailingThread)
    sync_service, account_service = _create_real_sync_service()
    client = _create_client(sync_service)

    route_response = client.post('/accounts/11/sync/start')

    assert route_response.status_code == 400
    assert route_response.json() == {
        'code': 1,
        'msg': 'RSS 同步启动失败: thread start failed',
        'data': None,
    }
    assert account_service.progress['running'] is False
    assert account_service.progress['phase'] == 'failed'
    assert account_service.sync_lock.acquire(blocking=False) is True
    account_service.sync_lock.release()


def test_start_rss_sync_releases_reservation_when_failure_recording_also_fails(monkeypatch):
    FailingThread.created = []
    monkeypatch.setattr('domains.rss.application.services.sync.service.Thread', FailingThread)
    sync_service, account_service = _create_real_sync_service()

    def fail_recording(*args, **kwargs):
        raise RuntimeError('failure recording failed')

    monkeypatch.setattr(sync_service, '_record_failure', fail_recording)
    client = _create_client(sync_service)

    route_response = client.post('/accounts/11/sync/start')

    assert route_response.status_code == 400
    assert route_response.json() == {
        'code': 1,
        'msg': 'RSS 同步启动失败: thread start failed',
        'data': None,
    }
    assert account_service.sync_lock.acquire(blocking=False) is True
    account_service.sync_lock.release()
