import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils import runtime_site_config


def test_runtime_site_config_merges_headers_and_exposes_sections():
    runtime_site_config.reset_runtime_site_state()
    runtime_site_config.set_site_configs({
        "youtube": {
            "http": {"headers": {"User-Agent": "UA"}},
            "login": {"headers": {"X-Login": "yes"}, "enabled": True},
            "proxy": {"enabled": True},
            "rate_limit": {"enabled": False},
        },
    })

    assert runtime_site_config.get_site_config("youtube") == {
        "http": {"headers": {"User-Agent": "UA"}},
        "login": {"headers": {"X-Login": "yes"}, "enabled": True},
        "proxy": {"enabled": True},
        "rate_limit": {"enabled": False},
    }
    assert runtime_site_config.get_http_headers("youtube", {"Accept": "json"}) == {
        "Accept": "json",
        "User-Agent": "UA",
    }
    assert runtime_site_config.get_login_config("youtube") == {
        "headers": {"X-Login": "yes"},
        "enabled": True,
    }
    assert runtime_site_config.get_login_headers("youtube", {"Accept": "json"}) == {
        "Accept": "json",
        "User-Agent": "UA",
        "X-Login": "yes",
    }
    assert runtime_site_config.get_proxy_config("youtube") == {"enabled": True}
    assert runtime_site_config.get_rate_limit_config("youtube") == {"enabled": False}
