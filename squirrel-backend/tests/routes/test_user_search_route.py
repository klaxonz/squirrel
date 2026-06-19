from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from domains.user.application.services.auth import get_current_user
from domains.user.interfaces.http.search import get_search_suggestion_service, router


class FakeSearchSuggestionService:
    def __init__(self):
        self.calls = []

    def list_search_suggestions(self, user_id, *, query, scope, limit):
        self.calls.append({'user_id': user_id, 'query': query, 'scope': scope, 'limit': limit})
        return [{'label': 'demo'}]


def test_search_suggestions_forwards_query_model_values():
    fake_service = FakeSearchSuggestionService()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    app.dependency_overrides[get_search_suggestion_service] = lambda: fake_service
    client = TestClient(app)

    route_response = client.get(
        '/api/search/suggestions',
        params={
            'query': 'sync',
            'scope': 'history',
            'limit': 12,
        },
    )

    assert route_response.status_code == 200
    assert route_response.json()['data'] == {
        'items': [{'label': 'demo'}],
        'scope': 'history',
        'query': 'sync',
    }
    assert fake_service.calls == [{'user_id': 7, 'query': 'sync', 'scope': 'history', 'limit': 12}]
