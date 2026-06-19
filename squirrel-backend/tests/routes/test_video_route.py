import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domains.user.application.services.auth import get_current_user
from domains.video.interfaces.http import router


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
        captured.update(
            {
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
            }
        )
        return [], None

    monkeypatch.setattr('domains.video.interfaces.http.listing.list_videos', fake_list_videos)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: type('User', (), {'id': 7})()
    client = TestClient(app)

    response = client.get('/api/video/list')

    assert response.status_code == 200
    assert response.json()['code'] == 0
    assert captured['user_id'] == 7
    assert captured['category'] == 'all'


def test_get_videos_forwards_query_model_values(monkeypatch):
    captured = {}

    def fake_list_videos(
        user_id,
        query,
        subscription_id,
        category,
        sort_by,
        nsfw,
        domains,
        cursor,
        page_size,
        **kwargs,
    ):
        captured.update(
            {
                'user_id': user_id,
                'query': query,
                'subscription_id': subscription_id,
                'category': category,
                'sort_by': sort_by,
                'nsfw': nsfw,
                'domains': domains,
                'cursor': cursor,
                'page_size': page_size,
                **kwargs,
            }
        )
        return [], None

    monkeypatch.setattr('domains.video.interfaces.http.listing.list_videos', fake_list_videos)
    monkeypatch.setattr(
        'domains.video.interfaces.http.listing.SiteCatalog.resolve_domains',
        classmethod(lambda cls, site: ['youtube.com'] if site == 'youtube' else []),
    )

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: type('User', (), {'id': 7})()
    client = TestClient(app)

    response = client.get(
        '/api/video/list',
        params={
            'query': 'abc',
            'subscription_id': 3,
            'category': 'liked',
            'sort_by': 'created_at',
            'nsfw': 'yes',
            'special': 'no',
            'site': 'youtube',
            'cursor': 'next-1',
            'pageSize': 33,
            'time_range': 'week',
            'duration': 'long',
            'content_type': 'PLAYLIST',
        },
    )

    assert response.status_code == 200
    assert response.json()['code'] == 0
    assert captured == {
        'user_id': 7,
        'query': 'abc',
        'subscription_id': 3,
        'category': 'liked',
        'sort_by': 'created_at',
        'nsfw': 'yes',
        'domains': ['youtube.com'],
        'cursor': 'next-1',
        'page_size': 33,
        'time_range': 'week',
        'duration': 'long',
        'content_type': 'PLAYLIST',
        'special': 'no',
    }
