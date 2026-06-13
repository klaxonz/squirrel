import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scheduling.tasks.cloudflare_heartbeat_task import CloudflareHeartbeatTask


def test_heartbeat_checks_health_instead_of_clearing_cache(monkeypatch):
    calls = []

    class _BypassClient:
        async def health(self):
            calls.append("health")

    monkeypatch.setattr("scheduling.tasks.cloudflare_heartbeat_task.get_default_client", lambda: _BypassClient())

    CloudflareHeartbeatTask.run()

    assert calls == ["health"]
