import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes.video_history import router
from utils.jwt_helper import get_current_user


def test_batch_update_history_forwards_reports_to_service(monkeypatch):
    captured = {}

    def fake_batch_update_histories(user_id, reports):
        captured["user_id"] = user_id
        captured["reports"] = reports

    monkeypatch.setattr("routes.video_history.video_history_service.batch_update_histories", fake_batch_update_histories)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: type("User", (), {"id": 7})()
    client = TestClient(app)

    response = client.post(
        "/api/video-history/batch-update",
        json={
            "reports": [
                {"video_id": 1, "last_position": 12.5, "timestamp": 1710000000000},
                {"video_id": 2, "last_position": 34, "timestamp": 1710000002000},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert captured["user_id"] == 7
    assert len(captured["reports"]) == 2
    assert captured["reports"][0].video_id == 1
    assert captured["reports"][0].last_position == 12.5
    assert captured["reports"][0].timestamp == 1710000000000
    assert captured["reports"][1].video_id == 2
    assert captured["reports"][1].last_position == 34
    assert captured["reports"][1].timestamp == 1710000002000
