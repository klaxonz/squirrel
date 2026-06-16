import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crawl import filter_cookies_to_query_string

from infrastructure.site_catalog import runtime_http


class DummyClient:
    pass


def test_get_cloudflare_bypass_client_defaults_to_none():
    runtime_http.reset_runtime_http_state()

    assert runtime_http.get_cloudflare_bypass_client() is None


def test_set_and_get_cloudflare_bypass_client():
    runtime_http.reset_runtime_http_state()
    client = DummyClient()

    runtime_http.set_cloudflare_bypass_client(client)

    assert runtime_http.get_cloudflare_bypass_client() is client


def test_set_cookie_file_resolver_updates_sdk_cookie_resolution(tmp_path):
    runtime_http.reset_runtime_http_state()
    cookie_file = tmp_path / "youtube.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".youtube.com\tTRUE\t/\tFALSE\t2147483647\tSID\tabc123\n",
        encoding="utf-8",
    )

    runtime_http.set_cookie_file_resolver(lambda _url: str(cookie_file))

    assert filter_cookies_to_query_string("https://www.youtube.com/watch?v=1") == "SID=abc123"


def test_set_cookie_domain_resolver_updates_sdk_cookie_domain_matching(tmp_path):
    runtime_http.reset_runtime_http_state()
    cookie_file = tmp_path / "youtube.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".youtube.com\tTRUE\t/\tFALSE\t2147483647\tSID\tabc123\n"
        ".googlevideo.com\tTRUE\t/\tFALSE\t2147483647\tGV\tignored\n",
        encoding="utf-8",
    )

    runtime_http.set_cookie_file_resolver(lambda _url: str(cookie_file))
    runtime_http.set_cookie_domain_resolver(lambda _url: "youtube.com")

    assert filter_cookies_to_query_string("https://rr4---sn-a5meknzl.googlevideo.com/videoplayback?c=MWEB") == "SID=abc123"
