import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domains.subscription.interfaces.http import basic as subscription_route
from domains.video.interfaces.http import listing as video_route


def _route_paths(router):
    return {route.path for route in router.routes}


def test_video_router_does_not_expose_download_endpoints():
    paths = _route_paths(video_route.router)

    assert "/api/video/download" not in paths
    assert "/api/video/play/{video_id}" not in paths


def test_subscription_router_does_not_expose_auto_download_toggles():
    paths = _route_paths(subscription_route.router)

    assert "/api/subscription/toggle-auto-download" not in paths
    assert "/api/subscription/toggle-download-all" not in paths
