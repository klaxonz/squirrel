from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from application.routes.logs import get_log_service, router
from domains.user.application.services.auth import get_current_user


class FakeLogService:
    def __init__(self):
        self.calls = []

    def read_log_lines(self, *, filename, keyword, level, start_line, limit):
        self.calls.append(
            {
                'filename': filename,
                'keyword': keyword,
                'level': level,
                'start_line': start_line,
                'limit': limit,
            }
        )
        return ['line one'], 9, True


def test_query_logs_forwards_query_model_values():
    fake_service = FakeLogService()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    app.dependency_overrides[get_log_service] = lambda: fake_service
    client = TestClient(app)

    route_response = client.get(
        '/api/logs/query',
        params={
            'filename': 'worker.log',
            'keyword': 'sync',
            'level': 'ERROR',
            'page': 3,
            'pageSize': 25,
        },
    )

    assert route_response.status_code == 200
    assert route_response.json()['data'] == {
        'logs': ['line one'],
        'total': 9,
        'page': 3,
        'page_size': 25,
        'has_more': True,
    }
    assert fake_service.calls == [
        {
            'filename': 'worker.log',
            'keyword': 'sync',
            'level': 'ERROR',
            'start_line': 50,
            'limit': 25,
        }
    ]
