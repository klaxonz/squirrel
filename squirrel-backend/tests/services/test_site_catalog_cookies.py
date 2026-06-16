import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import infrastructure.site_catalog.cookies as cookie


def test_filter_cookies_to_query_string_reads_matching_domain_cookies(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".youtube.com\tTRUE\t/\tFALSE\t2147483647\tSID\tabc123\n"
        ".example.com\tTRUE\t/\tFALSE\t2147483647\tTOKEN\tignored\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(cookie, "resolve_cookie_file_for_url", lambda url: str(cookie_file))

    assert cookie.filter_cookies_to_query_string("https://m.youtube.com/watch?v=1") == "SID=abc123"


def test_resolve_cookie_file_for_url_maps_youtube_media_domains(tmp_path, monkeypatch):
    cookie_file = tmp_path / "youtube.txt"
    cookie_file.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        cookie,
        "_get_cookie_site_catalog",
        lambda: {
            "youtube": {
                "domains": ["youtube.com", "youtu.be"],
                "cookie": {
                    "alias_domains": ["googlevideo.com", "gvt1.com", "ytimg.com"],
                    "match_domain": "youtube.com",
                },
            }
        },
        raising=False,
    )
    monkeypatch.setattr(cookie, "get_site_cookies_file_path", lambda slug: cookie_file if slug == "youtube" else tmp_path / "missing.txt")

    assert cookie.resolve_cookie_file_for_url("https://rr4---sn-a5meknzl.googlevideo.com/videoplayback") == str(cookie_file)


def test_filter_cookies_to_query_string_uses_youtube_cookie_domain_for_googlevideo_urls(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".youtube.com\tTRUE\t/\tFALSE\t2147483647\tSID\tabc123\n"
        ".googlevideo.com\tTRUE\t/\tFALSE\t2147483647\tGV\tignored\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(cookie, "resolve_cookie_file_for_url", lambda url: str(cookie_file))
    monkeypatch.setattr(
        cookie,
        "_get_cookie_site_catalog",
        lambda: {
            "youtube": {
                "domains": ["youtube.com", "youtu.be"],
                "cookie": {
                    "alias_domains": ["googlevideo.com", "gvt1.com", "ytimg.com"],
                    "match_domain": "youtube.com",
                },
            }
        },
        raising=False,
    )

    assert (
        cookie.filter_cookies_to_query_string("https://rr4---sn-a5meknzl.googlevideo.com/videoplayback?c=MWEB")
        == "SID=abc123"
    )


def test_filter_cookies_to_query_string_reads_cookie_file_every_call(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")

    load_calls = []

    class _FakeCookie:
        def __init__(self, domain, name, value):
            self.domain = domain
            self.name = name
            self.value = value

    class _FakeJar:
        def load(self, path, ignore_discard=True, ignore_expires=True):
            load_calls.append(Path(path).name)

        def __iter__(self):
            return iter([
                _FakeCookie(".youtube.com", "SID", "abc123"),
                _FakeCookie(".example.com", "TOKEN", "ignored"),
            ])

    monkeypatch.setattr(cookie, "resolve_cookie_file_for_url", lambda url: str(cookie_file))
    monkeypatch.setattr(cookie, "resolve_cookie_match_domain_for_url", lambda url: "youtube.com")
    monkeypatch.setattr(cookie.cookielib, "MozillaCookieJar", _FakeJar)

    first = cookie.filter_cookies_to_query_string("https://www.youtube.com/watch?v=1")
    second = cookie.filter_cookies_to_query_string("https://www.youtube.com/watch?v=2")

    assert first == "SID=abc123"
    assert second == "SID=abc123"
    assert load_calls == ["cookies.txt", "cookies.txt"]


def test_resolve_cookie_match_domain_for_url_uses_site_catalog_cookie_config(monkeypatch):
    monkeypatch.setattr(
        cookie,
        "_get_cookie_site_catalog",
        lambda: {
            "youtube": {
                "domains": ["youtube.com", "youtu.be"],
                "cookie": {
                    "alias_domains": ["googlevideo.com", "gvt1.com", "ytimg.com"],
                    "match_domain": "youtube.com",
                },
            }
        },
        raising=False,
    )

    assert cookie.resolve_cookie_match_domain_for_url("https://i.ytimg.com/vi/demo/hqdefault.jpg") == "youtube.com"


def test_resolve_cookie_file_for_url_uses_effective_site_catalog_defaults(tmp_path, monkeypatch):
    cookie_file = tmp_path / "youporn.txt"
    cookie_file.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        cookie,
        "_get_cookie_site_catalog",
        lambda: {
            "youtube": {
                "domains": ["youtube.com"],
            },
            "youporn": {
                "domains": ["youporn.com"],
            },
        },
        raising=False,
    )
    monkeypatch.setattr(
        cookie,
        "get_site_cookies_file_path",
        lambda slug: cookie_file if slug == "youporn" else tmp_path / f"{slug}.txt",
    )

    assert cookie.resolve_cookie_file_for_url("https://www.youporn.com/") == str(cookie_file)
