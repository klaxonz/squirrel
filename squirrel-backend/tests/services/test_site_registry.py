from pathlib import Path
from types import SimpleNamespace

from infrastructure.site_registry.registry import SiteRegistry


def _fake_runtime(slug, capabilities, descriptor_metadata=None):
    return SimpleNamespace(
        site_descriptor=lambda: {
            'site_name': slug,
            'domains': [f'{slug}.com'],
            'test_url': f'https://{slug}.com',
            'metadata': descriptor_metadata or {'label': slug.upper()},
        },
        start=lambda _context: None,
        stop=lambda: None,
        **{cap: (lambda _cap=cap: None) for cap in capabilities},
    )


def test_registry_loads_real_site_runtime_in_process():
    registry = SiteRegistry(repo_root=Path('.'))

    runtime = registry.get_site_runtime('youtube')

    assert runtime.site_descriptor()['site_name'] == 'youtube'
    for method in ('check_login_status', 'import_subscriptions', 'resolve_subscription', 'sync_subscription', 'extract_video'):
        assert callable(getattr(runtime, method))
    # cached: same object on second load
    assert registry.get_site_runtime('youtube') is runtime


def test_registry_unknown_site_raises_value_error():
    registry = SiteRegistry(repo_root=Path('.'))

    try:
        registry.get_site_runtime('javdb')
    except ValueError as exc:
        assert 'javdb' in str(exc)
    else:
        raise AssertionError('Expected ValueError for unknown site')


def test_registry_capability_queries_use_method_presence():
    registry = SiteRegistry(repo_root=Path('.'))
    registry._runtimes = {
        'youtube': _fake_runtime('youtube', ('check_login_status', 'sync_subscription')),
        'bilibili': _fake_runtime('bilibili', ('check_login_status',)),
    }

    assert registry.get_supported_sites('check_login_status') == {'youtube', 'bilibili'}
    assert registry.get_supported_sites('sync_subscription') == {'youtube'}
    assert registry.has_capability('youtube', 'sync_subscription') is True
    assert registry.has_capability('bilibili', 'sync_subscription') is False
    assert registry.has_capability('javdb', 'sync_subscription') is False


def test_registry_build_site_catalog_uses_descriptor():
    registry = SiteRegistry(repo_root=Path('.'))
    registry._runtimes = {
        'youtube': _fake_runtime(
            'youtube',
            ('check_login_status', 'import_subscriptions', 'resolve_subscription', 'sync_subscription', 'extract_video'),
            descriptor_metadata={'label': 'YouTube', 'aliases': ['yt'], 'metadata': {'requires_cookies': True}},
        ),
    }

    catalog = registry.build_site_catalog()

    assert catalog['youtube']['label'] == 'YouTube'
    assert catalog['youtube']['domains'] == ['youtube.com']
    assert catalog['youtube']['aliases'] == ['yt']
    assert catalog['youtube']['metadata']['requires_cookies'] is True
    assert catalog['youtube']['features'] == [
        'check_login_status',
        'import_subscriptions',
        'resolve_subscription',
        'sync_subscription',
        'extract_video',
    ]


def test_registry_find_site_by_domain_uses_catalog():
    registry = SiteRegistry(repo_root=Path('.'))
    registry._runtimes = {
        'youtube': _fake_runtime('youtube', ()),
        'bilibili': _fake_runtime('bilibili', ()),
    }

    assert registry.find_site_by_domain('www.youtube.com') == 'youtube'
    assert registry.find_site_by_domain('b23.tv') is None  # not in fake descriptors
    assert registry.find_site_by_domain(None) is None


def test_registry_start_all_and_stop_all_run_lifecycle_hooks():
    started = []
    stopped = []
    registry = SiteRegistry(repo_root=Path('.'))
    registry._runtimes = {
        'youtube': _fake_runtime('youtube', ()),
        'bilibili': _fake_runtime('bilibili', ()),
    }
    for slug in ('youtube', 'bilibili'):
        registry._runtimes[slug].start = lambda _context, s=slug: started.append(s)
        registry._runtimes[slug].stop = lambda s=slug: stopped.append(s)

    registry.start_all()
    registry.stop_all()

    assert sorted(started) == ['bilibili', 'youtube']
    assert sorted(stopped) == ['bilibili', 'youtube']
    assert registry._runtimes == {}


def test_registry_refresh_sites_is_a_noop():
    registry = SiteRegistry(repo_root=Path('.'))
    registry._runtimes['youtube'] = _fake_runtime('youtube', ())

    registry.refresh_sites({'YouTube', 'unknown'})

    assert 'youtube' in registry._runtimes
