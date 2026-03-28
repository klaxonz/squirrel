from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils import cookie


def test_filter_cookies_to_query_string_by_domain_uses_backend_resolver(monkeypatch):
    calls = []

    monkeypatch.setattr(
        cookie,
        'resolve_cookie_file_for_url',
        lambda url: calls.append(url) or 'D:/tmp/mock.txt',
    )
    monkeypatch.setattr(
        cookie,
        '_read_cookie_file_as_query_string',
        lambda path, target_url: 'a=1; b=2',
    )

    assert cookie.filter_cookies_to_query_string_by_domain('youtube.com') == 'a=1; b=2'
    assert calls == ['https://youtube.com']


def test_filter_cookies_to_query_string_reads_matching_domain_cookies(tmp_path, monkeypatch):
    cookie_file = tmp_path / 'cookies.txt'
    cookie_file.write_text(
        '# Netscape HTTP Cookie File\n'
        '.youtube.com\tTRUE\t/\tFALSE\t2147483647\tSID\tabc123\n'
        '.example.com\tTRUE\t/\tFALSE\t2147483647\tTOKEN\tignored\n',
        encoding='utf-8',
    )

    monkeypatch.setattr(cookie, 'resolve_cookie_file_for_url', lambda url: str(cookie_file))

    assert cookie.filter_cookies_to_query_string('https://m.youtube.com/watch?v=1') == 'SID=abc123'
