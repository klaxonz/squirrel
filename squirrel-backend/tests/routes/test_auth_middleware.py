import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes.middleware.auth import is_public_api_path


def test_site_icon_route_is_public_without_exposing_other_plugin_site_routes():
    assert is_public_api_path("/api/sites/youtube/icon") is True
    assert is_public_api_path("/api/sites/bilibili/icon") is True
    assert is_public_api_path("/api/sites") is False
    assert is_public_api_path("/api/sites/youtube/login-status") is False
    assert is_public_api_path("/api/sites/youtube/cookies") is False

