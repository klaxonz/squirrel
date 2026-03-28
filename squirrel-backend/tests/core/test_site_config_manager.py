from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core import site_config_manager
from utils import runtime_site_config


def test_apply_site_config_overrides_updates_backend_runtime_state(monkeypatch):
    calls: list[tuple[str, str, object]] = []

    monkeypatch.setattr(
        site_config_manager,
        'get_effective_site_catalog',
        lambda catalog=None: {
            'youtube': {
                'domains': ['youtube.com'],
                'http': {'headers': {'User-Agent': 'UA'}},
                'rate_limit': {
                    'enabled': False,
                    'min_interval': 1.0,
                    'max_interval': 2.0,
                },
            }
        },
    )
    monkeypatch.setattr(
        site_config_manager.backend_rate_limiter,
        'set_domain_enabled',
        lambda domain, enabled: calls.append(('enabled', domain, enabled)),
    )
    monkeypatch.setattr(
        site_config_manager.backend_rate_limiter,
        'add_rate_limit',
        lambda domain, min_interval, max_interval: calls.append(('limit', domain, (min_interval, max_interval))),
    )

    runtime_site_config.reset_runtime_site_state()

    site_config_manager.apply_site_config_overrides()

    assert runtime_site_config.get_http_headers('youtube') == {'User-Agent': 'UA'}
    assert runtime_site_config.get_rate_limit_config('youtube') == {
        'enabled': False,
        'min_interval': 1.0,
        'max_interval': 2.0,
    }
    assert calls == [
        ('enabled', 'youtube.com', False),
    ]
