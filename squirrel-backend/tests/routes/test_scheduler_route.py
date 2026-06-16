from fastapi import FastAPI
from fastapi.testclient import TestClient

from infrastructure.scheduling.routes.control import router
from infrastructure.scheduling.routes.dependencies import get_scheduled_task_service


class FakeScheduledTaskService:
    def __init__(self):
        self.calls = []

    def get_task_list(self, *, page, page_size, search, status, task_type):
        self.calls.append({
            'page': page,
            'page_size': page_size,
            'search': search,
            'status': status,
            'task_type': task_type,
        })
        return {
            'page': page,
            'page_size': page_size,
            'total': 1,
            'data': [{'id': 1, 'name': 'Demo Task'}],
        }


def test_scheduled_tasks_route_returns_paginated_task_list():
    fake_service = FakeScheduledTaskService()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_scheduled_task_service] = lambda: fake_service
    client = TestClient(app)

    route_response = client.get(
        '/api/scheduler/tasks',
        params={
            'page': 2,
            'page_size': 15,
            'search': 'demo',
            'status': 'enabled',
            'task_type': 'system',
        },
    )

    assert route_response.status_code == 200
    body = route_response.json()
    assert body['code'] == 0
    assert body['data'] == {
        'page': 2,
        'page_size': 15,
        'total': 1,
        'data': [{'id': 1, 'name': 'Demo Task'}],
    }
    assert fake_service.calls == [{
        'page': 2,
        'page_size': 15,
        'search': 'demo',
        'status': 'enabled',
        'task_type': 'system',
    }]
