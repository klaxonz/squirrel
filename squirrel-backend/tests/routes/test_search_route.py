import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes.search import router
from services.user.auth import get_current_user


def test_search_suggestions_route_passes_scope_and_limit(monkeypatch):
    captured = {}

    def fake_list_search_suggestions(user_id, query, scope, limit):
        captured.update({
            "user_id": user_id,
            "query": query,
            "scope": scope,
            "limit": limit,
        })
        return [{"type": "video", "value": "黑神话悟空", "label": "黑神话悟空", "meta": "视频"}]

    monkeypatch.setattr("routes.search.search_suggestion_service.list_search_suggestions", fake_list_search_suggestions)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: type("User", (), {"id": 9})()
    client = TestClient(app)

    response = client.get("/api/search/suggestions", params={"query": "黑神话", "scope": "history", "limit": 6})

    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert captured == {
        "user_id": 9,
        "query": "黑神话",
        "scope": "history",
        "limit": 6,
    }
    assert response.json()["data"]["items"][0]["value"] == "黑神话悟空"
