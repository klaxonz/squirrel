import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'squirrel-site-runtimes' / 'javdb' / 'src'))

import squirrel_javdb.proxy as javdb_proxy_module


def test_javdb_proxy_config_exposes_cross_host_bypass_domains():
    payload = {
        'domain': 'javdb.com',
        'target_url': 'https://surrit.com/example/video.m3u8',
        'referer': 'https://missav.ai/en/example-video',
    }

    config = javdb_proxy_module.build_runtime_proxy_config(payload)
    domain_config = config['domain_configs'][0]

    assert domain_config['domain'] == 'javdb.com'
    assert domain_config['bypass_domains'] == ['surrit.com']
    assert config['site_headers']['Referer'] == 'https://missav.ai/en/example-video'
    assert config['site_headers']['Origin'] == 'https://missav.ai'


def test_javdb_proxy_config_skips_cross_host_bypass_domains_for_media_segments():
    payload = {
        'domain': 'javdb.com',
        'target_url': 'https://surrit.com/example/1080p/video720.jpeg',
        'referer': 'https://missav.ai/en/example-video',
    }

    config = javdb_proxy_module.build_runtime_proxy_config(payload)
    domain_config = config['domain_configs'][0]

    assert domain_config['domain'] == 'javdb.com'
    assert 'bypass_domains' not in domain_config
    assert config['site_headers']['Referer'] == 'https://missav.ai/en/example-video'
    assert config['site_headers']['Origin'] == 'https://missav.ai'
