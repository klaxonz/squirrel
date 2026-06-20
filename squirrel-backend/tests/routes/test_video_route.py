import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domains.user.application.services.auth import get_current_user
from domains.video.interfaces.http import router
from domains.video.interfaces.http.dependencies import get_video_list_service


class FakeVideoListService:
    """Stand-in for VideoListService that records calls instead of hitting the DB."""

    def __init__(self):
        self.list_calls = []
        self.get_calls = []

    def list_videos(self, *args, **kwargs):
        # Match the historical positional signature so existing assertions hold.
        self.list_calls.append(
            {
                'user_id': args[0] if len(args) > 0 else kwargs.get('user_id'),
                'query': args[1] if len(args) > 1 else kwargs.get('query'),
                'subscription_id': args[2] if len(args) > 2 else kwargs.get('subscription_id'),
                'category': args[3] if len(args) > 3 else kwargs.get('category'),
                'sort_by': args[4] if len(args) > 4 else kwargs.get('sort_by'),
                'nsfw': args[5] if len(args) > 5 else kwargs.get('nsfw'),
                'domains': args[6] if len(args) > 6 else kwargs.get('domains'),
                'cursor': args[7] if len(args) > 7 else kwargs.get('cursor'),
                'page_size': args[8] if len(args) > 8 else kwargs.get('page_size'),
                **{k: v for k, v in kwargs.items() if k not in ('user_id', 'query', 'subscription_id', 'category', 'sort_by', 'nsfw', 'domains', 'cursor', 'page_size')},
            }
        )
        return [], None

    def get_video(self, user_id, video_id):
        self.get_calls.append({'user_id': user_id, 'video_id': video_id})
        return {'id': video_id}


def _build_client(service=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: type('User', (), {'id': 7})()
    if service is not None:
        app.dependency_overrides[get_video_list_service] = lambda: service
    return TestClient(app)


def test_get_videos_defaults_missing_category_to_all():
    service = FakeVideoListService()
    client = _build_client(service)

    response = client.get('/api/video/list')

    assert response.status_code == 200
    assert response.json()['code'] == 0
    assert service.list_calls[0]['user_id'] == 7
    assert service.list_calls[0]['category'] == 'all'


def test_get_videos_forwards_query_model_values(monkeypatch):
    service = FakeVideoListService()
    monkeypatch.setattr(
        'domains.video.interfaces.http.listing.SiteCatalog.resolve_domains',
        classmethod(lambda cls, site: ['youtube.com'] if site == 'youtube' else []),
    )
    client = _build_client(service)

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
    assert service.list_calls[0] == {
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
