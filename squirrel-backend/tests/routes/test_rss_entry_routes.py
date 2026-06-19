from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from domains.rss.interfaces.http.dependencies import get_rss_service
from domains.rss.interfaces.http.entries import router
from domains.user.application.services.auth import get_current_user


class FakeRssService:
    def __init__(self):
        self.calls = []

    def list_entries(self, user_id, *, account_id, feed_id, is_read, is_starred, page, page_size):
        self.calls.append(
            {
                'user_id': user_id,
                'account_id': account_id,
                'feed_id': feed_id,
                'is_read': is_read,
                'is_starred': is_starred,
                'page': page,
                'page_size': page_size,
            }
        )
        return {'data': [], 'total': 0, 'page': page, 'page_size': page_size}


def test_list_rss_entries_forwards_query_model_values():
    fake_service = FakeRssService()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    app.dependency_overrides[get_rss_service] = lambda: fake_service
    client = TestClient(app)

    route_response = client.get(
        '/entries',
        params={
            'accountId': 11,
            'feedId': 22,
            'isRead': 'true',
            'isStarred': 'false',
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
            'page': 3,
            'page_size': 40,
        }
    ]
