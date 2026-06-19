import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domains.subscription.interfaces.http.basic import router


@pytest.mark.parametrize(
    ('path', 'method'),
    [
        ('/api/subscription/sync-center/retry-failed', 'POST'),
        ('/api/subscription/sync-center/reconcile', 'POST'),
    ],
)
def test_manual_sync_center_action_routes_are_removed(path, method):
    registered_routes = {
        (route.path, request_method) for route in router.routes for request_method in route.methods or set()
    }

    assert (path, method) not in registered_routes
