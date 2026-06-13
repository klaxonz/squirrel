import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from application.middleware.auth import is_public_api_path


def test_exact_paths_are_public():
    assert is_public_api_path("/api/users/login") is True
    assert is_public_api_path("/api/users/register") is True
    assert is_public_api_path("/api/video/thumbnail") is True
    assert is_public_api_path("/docs") is True
    assert is_public_api_path("/redoc") is True
    assert is_public_api_path("/openapi.json") is True


def test_exact_paths_reject_prefix_bypass():
    assert is_public_api_path("/api/users/login_malicious") is False
    assert is_public_api_path("/api/users/register_admin") is False
    assert is_public_api_path("/api/video/thumbnail-admin") is False
    assert is_public_api_path("/docs_extra") is False
    assert is_public_api_path("/redoc_evil") is False


def test_health_prefix_matches_subpaths():
    assert is_public_api_path("/health") is True
    assert is_public_api_path("/health/") is True
    assert is_public_api_path("/health/ready") is True
    assert is_public_api_path("/health/live") is True


def test_health_prefix_rejects_prefix_bypass():
    assert is_public_api_path("/health_bad") is False
    assert is_public_api_path("/health_extra") is False


def test_site_icon_route_is_public_without_exposing_other_plugin_site_routes():
    assert is_public_api_path("/api/sites/youtube/icon") is True
    assert is_public_api_path("/api/sites/bilibili/icon") is True
    assert is_public_api_path("/api/sites") is False
    assert is_public_api_path("/api/sites/youtube/login-status") is False
    assert is_public_api_path("/api/sites/youtube/cookies") is False

