import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services import music_service


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200
        self.headers = {'content-type': 'application/json'}
        self.text = ''

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _InvalidJsonResponse:
    status_code = 200
    headers = {'content-type': 'text/html; charset=utf-8'}
    text = '<!doctype html><html><body>Not an API</body></html>'

    def raise_for_status(self):
        return None

    def json(self):
        raise ValueError('invalid json')


class _FakeClient:
    def __init__(self, calls, payload):
        self._calls = calls
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url, params=None, headers=None):
        self._calls.append({'url': url, 'params': params, 'headers': headers})
        return _FakeResponse(self._payload)


class _SequenceClient:
    def __init__(self, calls, payloads):
        self._calls = calls
        self._payloads = list(payloads)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url, params=None, headers=None):
        self._calls.append({'url': url, 'params': params, 'headers': headers})
        return _FakeResponse(self._payloads.pop(0))


class _FakeRedis:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value
        return True


def test_search_tracks_normalizes_kugou_response(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'data': {
            'total': 1,
            'lists': [
                {
                    'AlbumAudioID': 123,
                    'FileHash': 'ABC',
                    'SongName': 'Demo Song',
                    'SingerName': 'Demo Artist',
                    'AlbumName': 'Demo Album',
                    'AlbumID': 456,
                    'Duration': 210,
                    'Image': 'https://img.example.test/cover.jpg',
                }
            ],
        }
    }

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: _FakeClient(calls, payload))

    result = music_service.search_tracks(1, 'demo', 1, 20)

    assert result['total'] == 1
    assert result['items'] == [
        {
            'id': '123',
            'title': 'Demo Song',
            'artist': 'Demo Artist',
            'album': 'Demo Album',
            'hash': 'ABC',
            'album_id': '456',
            'album_audio_id': '123',
            'duration': 210,
            'cover': 'https://img.example.test/cover.jpg',
        }
    ]
    assert calls == [
        {
            'url': 'http://127.0.0.1:3000/search',
            'params': {'keywords': 'demo', 'page': 1, 'pagesize': 20, 'type': 'song'},
            'headers': {'Authorization': 'token=abc;userid=1;dfid=xyz'},
        }
    ]


def test_get_track_play_url_returns_direct_url(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'data': [
            {
                'quality': '128',
                'expire': 1800,
                'info': {
                    'tracker_url': [
                        'https://cdn.example.test/demo.mp3',
                        'https://cdn.example.test/demo-backup.mp3',
                    ],
                },
            }
        ]
    }

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: _FakeClient(calls, payload))

    result = music_service.get_track_play_url(1, 'ABC', '123', '128')

    assert result['url'] == 'https://cdn.example.test/demo.mp3'
    assert result['expires_at'] == 1800
    assert calls[0]['url'] == 'http://127.0.0.1:3000/song/url/new'
    assert calls[0]['params'] == {'hash': 'ABC', 'album_audio_id': '123'}
    assert calls[0]['headers'] == {}


def test_request_requires_configured_base_url(monkeypatch):
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', '')
    monkeypatch.setattr(music_service, 'redis_client', _FakeRedis())

    try:
        music_service.search_tracks(1, 'demo', 1, 20)
    except music_service.MusicServiceError as exc:
        assert str(exc) == 'KUGOU_MUSIC_API_BASE_URL is not configured'
    else:
        raise AssertionError('MusicServiceError was not raised')


def test_request_reports_non_json_response(monkeypatch):
    calls = []
    redis = _FakeRedis()

    class _InvalidJsonClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, params=None, headers=None):
            calls.append({'url': url, 'params': params, 'headers': headers})
            return _InvalidJsonResponse()

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: _InvalidJsonClient())

    try:
        music_service.search_tracks(1, 'demo', 1, 20)
    except music_service.MusicServiceError as exc:
        message = str(exc)
        assert 'KuGouMusicApi returned non-JSON response' in message
        assert 'content_type=text/html; charset=utf-8' in message
        assert 'Not an API' in message
    else:
        raise AssertionError('MusicServiceError was not raised')


def test_create_qr_login_returns_key_and_image(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payloads = [
        {'data': {'qrcode': 'qr-demo'}},
        {'data': {'url': 'https://h5.kugou.com/login?qrcode=qr-demo', 'base64': 'data:image/png;base64,abc'}},
    ]

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: client)

    result = music_service.create_qr_login()

    assert result == {
        'key': 'qr-demo',
        'url': 'https://h5.kugou.com/login?qrcode=qr-demo',
        'base64': 'data:image/png;base64,abc',
    }
    assert calls[0]['url'] == 'http://127.0.0.1:3000/login/qr/key'
    assert calls[1]['url'] == 'http://127.0.0.1:3000/login/qr/create'
    assert calls[1]['params'] == {'key': 'qr-demo', 'qrimg': 1}


def test_check_qr_login_saves_redis_cookie(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payloads = [
        {'data': {'status': 4, 'token': 'token-demo', 'userid': 42}},
        {'data': {'dfid': 'dfid-demo'}},
    ]

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    monkeypatch.setattr(music_service, '_timestamp_ms', lambda: 1000)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: client)

    result = music_service.check_qr_login(1, 'qr-demo')

    assert result['logged_in'] is True
    assert result['auth'] == {'logged_in': True, 'source': 'redis', 'userid': '42'}
    assert redis.values['music:kugou:auth:1'] == 'token=token-demo;userid=42;dfid=dfid-demo'
    assert calls == [
        {
            'url': 'http://127.0.0.1:3000/login/qr/check',
            'params': {'key': 'qr-demo', 'timestamp': 1000},
            'headers': {},
        },
        {
            'url': 'http://127.0.0.1:3000/register/dev',
            'params': {},
            'headers': {},
        },
    ]


def test_search_tracks_prefers_redis_cookie(monkeypatch):
    calls = []
    redis = _FakeRedis()
    redis.set('music:kugou:auth:1', 'token=redis-token;userid=9;dfid=redis-dfid')
    payload = {'data': {'total': 0, 'lists': []}}

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', 'token=env-token;userid=1;dfid=env-dfid')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: _FakeClient(calls, payload))

    music_service.search_tracks(1, 'demo', 1, 20)

    assert calls[0]['headers'] == {'Authorization': 'token=redis-token;userid=9;dfid=redis-dfid'}
