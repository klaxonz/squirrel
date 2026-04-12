from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes.video import router
from utils.jwt_helper import get_current_user


def test_get_videos_defaults_missing_category_to_all(monkeypatch):
    captured = {}

    def fake_list_videos(
        user_id,
        query,
        subscription_id,
        category,
        sort_by,
        nsfw,
        domains,
        page,
        page_size,
        with_total=False,
        **_,
    ):
        captured.update({
            'user_id': user_id,
            'query': query,
            'subscription_id': subscription_id,
            'category': category,
            'sort_by': sort_by,
            'nsfw': nsfw,
            'domains': domains,
            'page': page,
            'page_size': page_size,
            'with_total': with_total,
        })
        return [], None

    monkeypatch.setattr('routes.video.video_service.list_videos', fake_list_videos)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: type('User', (), {'id': 7})()
    client = TestClient(app)

    response = client.get('/api/video/list')

    assert response.status_code == 200
    assert response.json()['code'] == 0
    assert captured['user_id'] == 7
    assert captured['category'] == 'all'


def test_update_sites_catalog_accepts_override_payload(monkeypatch):
    monkeypatch.setattr(
        'routes.video.save_site_overrides',
        lambda payload: {'youtube': {'enabled': False, 'domains': ['youtube.com']}},
        raising=False,
    )

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.put('/api/sites', json={'sites': {'youtube': {'enabled': False}}})

    assert response.status_code == 200
    assert response.json()['code'] == 0
    assert response.json()['data']['youtube']['enabled'] is False
