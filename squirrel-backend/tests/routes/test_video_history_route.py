import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domains.user.application.services.auth import get_current_user
from domains.video.interfaces.http.history import get_video_history_service, router


def test_batch_update_history_forwards_reports_to_service():
    captured = {}

    class FakeVideoHistoryService:
        @staticmethod
        def batch_update_histories(user_id, reports):
            captured['user_id'] = user_id
            captured['reports'] = reports

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: type('User', (), {'id': 7})()
    app.dependency_overrides[get_video_history_service] = lambda: FakeVideoHistoryService()
    client = TestClient(app)

    response = client.post(
        '/api/video-history/batch-update',
        json={
            'reports': [
                {'video_id': 1, 'last_position': 12.5, 'timestamp': 1710000000000},
                {'video_id': 2, 'last_position': 34, 'timestamp': 1710000002000},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()['code'] == 0
    assert captured['user_id'] == 7
    assert len(captured['reports']) == 2
    assert captured['reports'][0].video_id == 1
    assert captured['reports'][0].last_position == 12.5
    assert captured['reports'][0].timestamp == 1710000000000
    assert captured['reports'][1].video_id == 2
    assert captured['reports'][1].last_position == 34
    assert captured['reports'][1].timestamp == 1710000002000


def test_clear_history_uses_current_user_id():
    captured = {}

    class FakeVideoHistoryService:
        @staticmethod
        def clear_histories(user_id, video_ids):
            captured['user_id'] = user_id
            captured['video_ids'] = video_ids

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: type('User', (), {'id': 7})()
    app.dependency_overrides[get_video_history_service] = lambda: FakeVideoHistoryService()
    client = TestClient(app)

    response = client.post('/api/video-history/clear', json=[1, 2])

    assert response.status_code == 200
    assert response.json()['code'] == 0
    assert captured == {'user_id': 7, 'video_ids': [1, 2]}
