import json
from unittest.mock import patch

from infrastructure.site_catalog.cookiecloud import CookieCloudService


def test_sync_cookiecloud_to_site_files_uses_safe_cookie_file_writer(tmp_path):
    writes = []

    with (
        patch.object(CookieCloudService, 'fetch_cookiecloud_cookie_data', return_value={
            'www.youtube.com': [
                {
                    'domain': '.youtube.com',
                    'name': 'SID',
                    'value': 'abc123',
                    'path': '/',
                    'secure': False,
                    'httpOnly': False,
                    'expirationDate': 2147483647,
                },
            ],
        }),
        patch('infrastructure.site_catalog.cookiecloud.get_effective_site_catalog', return_value={
            'youtube': {
                'domains': ['youtube.com'],
            },
        }),
        patch('infrastructure.site_catalog.cookiecloud.get_site_cookies_dir', return_value=tmp_path),
        patch('infrastructure.site_catalog.cookiecloud.get_site_cookies_file_path', lambda slug: tmp_path / f'{slug}.txt'),
        patch('infrastructure.site_catalog.cookiecloud.write_cookie_text_file', lambda path, content: writes.append((path, content))),
    ):
        result = CookieCloudService.sync_cookiecloud_to_site_files()

    assert result['updated_sites'] == 1
    assert writes == [
        (
            tmp_path / 'youtube.txt',
            '# Netscape HTTP Cookie File\n'
            '.youtube.com\tTRUE\t/\tFALSE\t2147483647\tSID\tabc123\n',
        ),
    ]


def test_fetch_cookiecloud_cookie_data_handles_response_text_decode_failure():
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
                },
            ],
        },
    }

    class FakeClient:
        def __init__(self, url, uuid, password):
            self.url = url
            self.uuid = uuid
            self.password = password

        def get_the_key(self):
            return '0123456789abcdef'

    with (
        patch.object(CookieCloudService, '_get_cookiecloud_config', return_value=('https://cookiecloud.example.com', 'uuid-1', 'password-1')),
        patch('infrastructure.site_catalog.cookiecloud.requests.get', return_value=FakeResponse()),
        patch('infrastructure.site_catalog.cookiecloud.PyCookieCloud', FakeClient),
        patch('infrastructure.site_catalog.cookiecloud.decrypt', lambda encrypted, key: json.dumps(fake_cookie_payload).encode('utf-8')),
    ):
        result = CookieCloudService.fetch_cookiecloud_cookie_data()

    assert 'www.youtube.com' in result
