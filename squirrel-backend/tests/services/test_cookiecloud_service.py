from pathlib import Path
import json
import sys
from types import SimpleNamespace

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


def test_fetch_cookiecloud_cookie_data_handles_response_text_decode_failure(monkeypatch):
    class FakeResponse:
        encoding = 'utf-8'
        apparent_encoding = 'latin-1'
        content = b'{"encrypted":"ciphertext"}'

        @property
        def text(self):
            raise UnicodeDecodeError('utf-8', b'\xc0', 0, 1, 'invalid start byte')

        def raise_for_status(self):
            return None

    fake_cookie_payload = {
        'cookie_data': {
            'www.youtube.com': [
                {
                    'domain': '.youtube.com',
                    'name': 'SID',
                    'value': 'abc123',
                    'path': '/',
                }
            ]
        }
    }

    monkeypatch.setattr(
        cookiecloud_service,
        '_get_cookiecloud_config',
        lambda: ('https://cookiecloud.example.com', 'uuid-1', 'password-1'),
    )
    monkeypatch.setattr(cookiecloud_service.requests, 'get', lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(
        cookiecloud_service,
        'PyCookieCloud',
        SimpleNamespace,
        raising=False,
    )

    class FakeClient:
        def __init__(self, url, uuid, password):
            self.url = url
            self.uuid = uuid
            self.password = password

        def get_the_key(self):
            return '0123456789abcdef'

    monkeypatch.setitem(
        sys.modules,
        'PyCookieCloud',
        SimpleNamespace(PyCookieCloud=FakeClient),
    )
    monkeypatch.setitem(
        sys.modules,
        'PyCookieCloud.PyCryptoJS',
        SimpleNamespace(decrypt=lambda encrypted, key: json.dumps(fake_cookie_payload).encode('utf-8')),
    )

    result = cookiecloud_service.fetch_cookiecloud_cookie_data()

    assert 'www.youtube.com' in result
