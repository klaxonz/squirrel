import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crawl import filter_cookies_to_query_string, get_rate_limiter
from crawl import utils as crawl_utils

from infrastructure.site_catalog import runtime_http
from infrastructure.site_runtimes import bridge_runtime_state
from infrastructure.site_runtimes.bridge_runtime_state import configure_backend_runtime_state


def test_bridge_runtime_state_configures_cookies_from_site_config(monkeypatch, tmp_path):
    cookie_file = tmp_path / 'bilibili.txt'
    cookie_file.write_text(
        '# Netscape HTTP Cookie File\n'
        '.bilibili.com\tTRUE\t/\tFALSE\t2147483647\tSESSDATA\tabc123\n',
        encoding='utf-8',
    )
    site_configs = {
        'bilibili': {
            'domains': ['bilibili.com', 'b23.tv'],
            'rate_limit': {
                'enabled': True,
                'min_interval': 3.0,
                'max_interval': 5.0,
            },
            'cookie': {
                'alias_domains': ['hdslb.com'],
                'match_domain': 'bilibili.com',
            },
        },
    }

    monkeypatch.setattr(bridge_runtime_state, 'get_site_cookies_file_path', lambda _site_name: cookie_file)
    runtime_http.reset_runtime_http_state()

    configure_backend_runtime_state(site_configs)

    assert crawl_utils._cookie_file_resolver is not None
    assert filter_cookies_to_query_string('https://space.bilibili.com/42') == 'SESSDATA=abc123'
    assert filter_cookies_to_query_string('https://i0.hdslb.com/bfs/archive/demo.jpg') == 'SESSDATA=abc123'
    rate_limit = get_rate_limiter().get_rate_limit('api.bilibili.com')
    assert rate_limit.min_interval == 3.0
    assert rate_limit.max_interval == 5.0
