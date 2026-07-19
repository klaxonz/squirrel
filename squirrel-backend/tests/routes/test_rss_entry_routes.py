from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from domains.rss.interfaces.http.dependencies import get_rss_service
from domains.rss.interfaces.http.entries import router
from domains.user.application.services.auth import get_current_user


class FakeRssService:
    def __init__(self):
        self.calls = []

    def list_entries(self, user_id, *, account_id, feed_id, is_read, is_starred, query, page, page_size):
        self.calls.append(
            {
                'user_id': user_id,
                'account_id': account_id,
                'feed_id': feed_id,
                'is_read': is_read,
                'is_starred': is_starred,
                'query': query,
                'page': page,
                'page_size': page_size,
            }
        )
        return {'data': [], 'total': 0, 'page': page, 'page_size': page_size}

    def record_entry_view(self, user_id, entry_id):
        self.calls.append({'method': 'record_entry_view', 'user_id': user_id, 'entry_id': entry_id})
        return False

    def list_recently_viewed(self, user_id, *, account_id=None):
        self.calls.append({'method': 'list_recently_viewed', 'user_id': user_id, 'account_id': account_id})
        return []


def _create_client(fake_service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    app.dependency_overrides[get_rss_service] = lambda: fake_service
    return TestClient(app)


def test_list_rss_entries_forwards_query_model_values():
    fake_service = FakeRssService()

    client = _create_client(fake_service)

    route_response = client.get(
        '/entries',
        params={
            'accountId': 11,
            'feedId': 22,
            'isRead': 'true',
            'isStarred': 'false',
            'query': 'security',
            'page': 3,
            'pageSize': 40,
        },
    )

    assert route_response.status_code == 200
    assert route_response.json()['data'] == {'data': [], 'total': 0, 'page': 3, 'page_size': 40}
    assert fake_service.calls == [
        {
            'user_id': 7,
            'account_id': 11,
            'feed_id': 22,
            'is_read': True,
            'is_starred': False,
            'query': 'security',
            'page': 3,
            'page_size': 40,
        }
    ]


def test_record_rss_entry_view_returns_not_found_when_entry_is_not_owned():
    fake_service = FakeRssService()
    response = _create_client(fake_service).post('/entries/99/view')

    assert response.status_code == 404
    assert fake_service.calls == [{'method': 'record_entry_view', 'user_id': 7, 'entry_id': 99}]


def test_recently_viewed_forwards_account_scope():
    fake_service = FakeRssService()
    response = _create_client(fake_service).get('/entries/recently-viewed', params={'accountId': 11})

    assert response.status_code == 200
    assert response.json()['data'] == {'data': []}
    assert fake_service.calls == [{'method': 'list_recently_viewed', 'user_id': 7, 'account_id': 11}]
