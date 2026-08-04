import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infrastructure.runtime import site_config_manager
from infrastructure.site_catalog import runtime_config as runtime_site_config


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
            },
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


def test_apply_site_config_overrides_updates_shared_rate_limiter(monkeypatch):
    backend_calls: list[tuple[str, str, object]] = []
    runtime_calls: list[tuple[str, str, object]] = []

    monkeypatch.setattr(
        site_config_manager,
        'get_effective_site_catalog',
        lambda catalog=None: {
            'youtube': {
                'domains': ['youtube.com'],
                'rate_limit': {
                    'enabled': True,
                    'min_interval': 5.0,
                    'max_interval': 8.0,
                },
            },
        },
    )
    monkeypatch.setattr(
        site_config_manager.backend_rate_limiter,
        'set_domain_enabled',
        lambda domain, enabled: backend_calls.append(('enabled', domain, enabled)),
    )
    monkeypatch.setattr(
        site_config_manager.backend_rate_limiter,
        'add_rate_limit',
        lambda domain, min_interval, max_interval: backend_calls.append(
            ('limit', domain, (min_interval, max_interval)),
        ),
    )
    monkeypatch.setattr(
        site_config_manager,
        'configure_crawl_rate_limit_enabled',
        lambda domain, enabled: runtime_calls.append(('enabled', domain, enabled)),
        raising=False,
    )
    monkeypatch.setattr(
        site_config_manager,
        'configure_crawl_rate_limit',
        lambda domain, min_interval, max_interval: runtime_calls.append(
            ('limit', domain, (min_interval, max_interval)),
        ),
        raising=False,
    )

    site_config_manager.apply_site_config_overrides()

    assert backend_calls == [
        ('enabled', 'youtube.com', True),
        ('limit', 'youtube.com', (5.0, 8.0)),
    ]
    assert runtime_calls == [
        ('enabled', 'youtube.com', True),
        ('limit', 'youtube.com', (5.0, 8.0)),
    ]


def test_get_effective_site_catalog_merges_site_defaults_with_overrides(monkeypatch):
    monkeypatch.setattr(
        site_config_manager,
        'build_site_catalog',
        lambda: {
            'bilibili': {
                'label': 'Bilibili',
                'domains': ['bilibili.com'],
                'enabled': True,
                'proxy': {'read_timeout': 180.0},
            },
        },
        raising=False,
    )

    catalog = site_config_manager.get_effective_site_catalog(
        {
            'bilibili': {
                'enabled': False,
                'proxy': {'read_timeout': 240.0},
            },
        }
    )

    assert catalog['bilibili']['enabled'] is False
    assert catalog['bilibili']['proxy']['read_timeout'] == 240.0
    assert catalog['bilibili']['domains'] == ['bilibili.com']


def test_get_effective_site_catalog_warns_on_unknown_override_keys(monkeypatch, caplog):
    import logging

    monkeypatch.setattr(
        site_config_manager,
        'build_site_catalog',
        lambda: {
            'youtube': {
                'label': 'YouTube',
                'domains': ['youtube.com'],
                'enabled': True,
            },
        },
        raising=False,
    )

    with caplog.at_level(logging.WARNING, logger='infrastructure.runtime.site_config_manager'):
        catalog = site_config_manager.get_effective_site_catalog(
            {
                'youtube': {
                    'enabled': False,
                    'rate_limt': {'enabled': True},  # typo of rate_limit
                },
            }
        )

    assert catalog['youtube']['enabled'] is False
    assert 'rate_limt' in caplog.text
    assert 'youtube' in caplog.text
    assert catalog['youtube'].get('rate_limt') is None
