import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services import youtube_oauth_service


def test_get_oauth_state_delegates_to_daemon_status(monkeypatch):
    expected = youtube_oauth_service.YouTubeOAuthState(status="authenticated")
    monkeypatch.setattr(youtube_oauth_service, "poll_oauth_status_via_daemon", lambda timeout_seconds=5.0: expected)

    result = youtube_oauth_service.get_oauth_state()

    assert result is expected


def test_get_oauth_cache_scope_uses_file_digest(monkeypatch, tmp_path):
    state_file = tmp_path / "youtube_oauth.json"
    state_file.write_text('{"credentials":{"access_token":"abc"}}', encoding="utf-8")
    monkeypatch.setattr(youtube_oauth_service, "_get_oauth_state_file", lambda: state_file)

    first = youtube_oauth_service.get_oauth_cache_scope()
    state_file.write_text('{"credentials":{"access_token":"xyz"}}', encoding="utf-8")
    second = youtube_oauth_service.get_oauth_cache_scope()

    assert first.startswith("oauth:")
    assert second.startswith("oauth:")
    assert first != second


def test_get_oauth_cache_scope_returns_none_when_file_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(youtube_oauth_service, "_get_oauth_state_file", lambda: tmp_path / "missing.json")

    assert youtube_oauth_service.get_oauth_cache_scope() == "oauth:none"
