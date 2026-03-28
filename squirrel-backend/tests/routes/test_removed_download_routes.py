from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes import subscription as subscription_route
from routes import video as video_route


def _route_paths(router):
    return {route.path for route in router.routes}


def test_video_router_does_not_expose_download_endpoints():
    paths = _route_paths(video_route.router)

    assert '/api/video/download' not in paths
    assert '/api/video/play/{video_id}' not in paths


def test_subscription_router_does_not_expose_auto_download_toggles():
    paths = _route_paths(subscription_route.router)

    assert '/api/subscription/toggle-auto-download' not in paths
    assert '/api/subscription/toggle-download-all' not in paths
