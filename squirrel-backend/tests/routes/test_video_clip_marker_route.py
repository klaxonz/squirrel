import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes.video_clip_marker import get_clip_marker_service, router
from services.user.auth import get_current_user


def test_create_clip_marker_forwards_payload_to_service():
    captured = {}

    class FakeClipMarkerService:
        @staticmethod
        def create_marker(user_id, data):
            captured["user_id"] = user_id
            captured["data"] = data
            return {
                "id": 11,
                "video_id": data.video_id,
                "title": data.title,
                "start_time": data.start_time,
                "end_time": data.end_time,
            }

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: type("User", (), {"id": 7})()
    app.dependency_overrides[get_clip_marker_service] = lambda: FakeClipMarkerService()
    client = TestClient(app)

    response = client.post(
        "/api/video-clip-markers",
        json={
            "video_id": 5,
            "title": "Share moment",
            "start_time": 12.5,
            "end_time": 21,
        },
    )

    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert captured["user_id"] == 7
    assert captured["data"].video_id == 5
    assert captured["data"].title == "Share moment"
    assert captured["data"].start_time == 12.5
    assert captured["data"].end_time == 21


def test_update_clip_marker_returns_not_found_when_service_misses():
    class FakeClipMarkerService:
        @staticmethod
        def update_marker(user_id, marker_id, data):
            return None

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: type("User", (), {"id": 9})()
    app.dependency_overrides[get_clip_marker_service] = lambda: FakeClipMarkerService()
    client = TestClient(app)

    response = client.put(
        "/api/video-clip-markers/99",
        json={
            "title": "Updated title",
            "start_time": 3,
            "end_time": 9,
        },
    )

    assert response.status_code == 404
    assert response.json()["code"] == 404
    assert response.json()["msg"] == "片段标记不存在"


def test_upload_clip_marker_preview_forwards_payload_to_service():
    captured = {}

    class FakeClipMarkerService:
        @staticmethod
        def save_preview(user_id, marker_id, image_data_url):
            captured["user_id"] = user_id
            captured["marker_id"] = marker_id
            captured["image_data_url"] = image_data_url
            return {
                "id": marker_id,
                "preview_image_url": "/static/clip-markers/user_7/video_5/marker_11.jpg?v=1",
            }

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: type("User", (), {"id": 7})()
    app.dependency_overrides[get_clip_marker_service] = lambda: FakeClipMarkerService()
    client = TestClient(app)

    response = client.post(
        "/api/video-clip-markers/11/preview",
        json={
            "image_data_url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAX/xAAXAQEBAQEAAAAAAAAAAAAAAAABAAID/9oADAMBAAIQAxAAAAFqgP/EABQQAQAAAAAAAAAAAAAAAAAAACD/2gAIAQEAAQUCX//EABQRAQAAAAAAAAAAAAAAAAAAACD/2gAIAQMBAT8BX//EABQRAQAAAAAAAAAAAAAAAAAAACD/2gAIAQIBAT8BX//Z",
        },
    )

    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert captured["user_id"] == 7
    assert captured["marker_id"] == 11
    assert captured["image_data_url"].startswith("data:image/jpeg;base64,")
