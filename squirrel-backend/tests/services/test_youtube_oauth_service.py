
from infrastructure.site_catalog.youtube_oauth import YouTubeOauthService, YouTubeOAuthState


def test_get_oauth_state_delegates_to_daemon_status():
    service = YouTubeOauthService()
    expected = YouTubeOAuthState(status="authenticated")
    service.poll_oauth_status_via_daemon = lambda timeout_seconds=5.0: expected

    result = service.get_oauth_state()

    assert result is expected


def test_get_oauth_cache_scope_uses_file_digest(tmp_path):
    service = YouTubeOauthService()
    state_file = tmp_path / "youtube_oauth.json"
    state_file.write_text('{"credentials":{"access_token":"abc"}}', encoding="utf-8")
    service._oauth_file = state_file

    first = service.get_oauth_cache_scope()
    state_file.write_text('{"credentials":{"access_token":"xyz"}}', encoding="utf-8")
    second = service.get_oauth_cache_scope()

    assert first.startswith("oauth:")
    assert second.startswith("oauth:")
    assert first != second


def test_get_oauth_cache_scope_returns_none_when_file_is_missing(tmp_path):
    service = YouTubeOauthService()
    service._oauth_file = tmp_path / "missing.json"

    assert service.get_oauth_cache_scope() == "oauth:none"
