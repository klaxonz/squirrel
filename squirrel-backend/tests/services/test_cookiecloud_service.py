from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services import cookiecloud_service


def test_sync_cookiecloud_to_site_files_uses_safe_cookie_file_writer(monkeypatch, tmp_path):
    writes = []

    monkeypatch.setattr(
        cookiecloud_service,
        'fetch_cookiecloud_cookie_data',
        lambda: {
            'www.youtube.com': [
                {
                    'domain': '.youtube.com',
                    'name': 'SID',
                    'value': 'abc123',
                    'path': '/',
                    'secure': False,
                    'httpOnly': False,
                    'expirationDate': 2147483647,
                }
            ]
        },
    )
    monkeypatch.setattr(
        cookiecloud_service,
        'get_effective_site_catalog',
        lambda: {
            'youtube': {
                'domains': ['youtube.com'],
            }
        },
    )
    monkeypatch.setattr(cookiecloud_service, 'get_site_cookies_dir', lambda: tmp_path)
    monkeypatch.setattr(cookiecloud_service, 'get_site_cookies_file_path', lambda slug: tmp_path / f'{slug}.txt')
    monkeypatch.setattr(
        cookiecloud_service,
        'write_cookie_text_file',
        lambda path, content: writes.append((path, content)),
        raising=False,
    )

    result = cookiecloud_service.sync_cookiecloud_to_site_files()

    assert result['updated_sites'] == 1
    assert writes == [
        (
            tmp_path / 'youtube.txt',
            '# Netscape HTTP Cookie File\n'
            '.youtube.com\tTRUE\t/\tFALSE\t2147483647\tSID\tabc123\n',
        )
    ]
