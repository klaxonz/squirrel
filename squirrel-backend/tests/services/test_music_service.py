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
        'bitRate': 128000,
        'expire': 1800,
        'url': [
            'https://cdn.example.test/demo.mp3',
            'https://cdn.example.test/demo-backup.mp3',
        ],
    }

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: _FakeClient(calls, payload))

    result = music_service.get_track_play_url(1, 'ABC', '123', '128')

    assert result['url'] == 'https://cdn.example.test/demo.mp3'
    assert result['expires_at'] == 1800
    assert calls[0]['url'] == 'http://127.0.0.1:3000/song/url'
    assert calls[0]['params'] == {'hash': 'ABC', 'quality': '128', 'album_audio_id': '123'}
    assert calls[0]['headers'] == {}


def test_get_track_play_url_returns_string_url(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'bitRate': 128000,
        'url': 'https://cdn.example.test/demo.mp3',
    }

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: _FakeClient(calls, payload))

    result = music_service.get_track_play_url(1, 'ABC', '123', '128')

    assert result['url'] == 'https://cdn.example.test/demo.mp3'


def test_get_track_lyric_returns_timed_lines(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payloads = [
        {'status': 200, 'candidates': [{'id': 'lyric-1', 'accesskey': 'access-1'}]},
        {'status': 200, 'decodeContent': '[00:01.00]First line\n[00:03.50][00:04.00]Repeat line\n[ti:Demo]'},
    ]

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: client)

    result = music_service.get_track_lyric(1, 'Demo Song', 'Demo Artist', 'ABC', '123', 210)

    assert result['lines'] == [
        {'time': 1.0, 'text': 'First line'},
        {'time': 3.5, 'text': 'Repeat line'},
        {'time': 4.0, 'text': 'Repeat line'},
    ]
    assert calls[0]['url'] == 'http://127.0.0.1:3000/search/lyric'
    assert calls[0]['params'] == {
        'keywords': 'Demo Artist - Demo Song',
        'hash': 'ABC',
        'album_audio_id': '123',
        'duration': 210,
        'man': 'no',
    }
    assert calls[1]['url'] == 'http://127.0.0.1:3000/lyric'
    assert calls[1]['params'] == {
        'id': 'lyric-1',
        'accesskey': 'access-1',
        'fmt': 'lrc',
        'decode': 'true',
    }


def test_list_ranks_normalizes_items(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'data': {
            'total': 1,
            'info': [
                {
                    'rankid': 8888,
                    'rank_cid': 115390,
                    'rankname': 'TOP500',
                    'imgurl': 'http://img.example.test/{size}/rank.jpg',
                    'intro': 'Demo rank',
                    'update_frequency': 'Daily',
                    'play_times': 1234,
                }
            ],
        }
    }

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: _FakeClient(calls, payload))

    result = music_service.list_ranks(1)

    assert result == {
        'items': [
            {
                'id': '8888',
                'rank_cid': '115390',
                'name': 'TOP500',
                'cover': 'http://img.example.test/240/rank.jpg',
                'intro': 'Demo rank',
                'update_frequency': 'Daily',
                'play_count': 1234,
            }
        ],
        'total': 1,
    }
    assert calls[0]['url'] == 'http://127.0.0.1:3000/rank/list'
    assert calls[0]['params'] == {'withsong': 0}


def test_get_rank_tracks_normalizes_items(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'total': 1,
        'data': {
            'songlist': [
                {
                    'songname': 'Rank Song',
                    'author_name': 'Rank Artist',
                    'album_audio_id': 123,
                    'album_id': 456,
                    'audio_info': {'hash_128': 'HASH', 'duration_128': 208000},
                    'album_info': {
                        'album_name': 'Rank Album',
                        'sizable_cover': 'http://img.example.test/{size}/cover.jpg',
                    },
                }
            ]
        },
    }

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: _FakeClient(calls, payload))

    result = music_service.get_rank_tracks(1, '8888', '115390', 2, 10)

    assert result['total'] == 1
    assert result['items'][0] == {
        'id': '123',
        'title': 'Rank Song',
        'artist': 'Rank Artist',
        'album': 'Rank Album',
        'hash': 'HASH',
        'album_id': '456',
        'album_audio_id': '123',
        'duration': 208,
        'cover': 'http://img.example.test/240/cover.jpg',
    }
    assert calls[0]['url'] == 'http://127.0.0.1:3000/rank/audio'
    assert calls[0]['params'] == {'rankid': '8888', 'page': 2, 'pagesize': 10, 'rank_cid': '115390'}


def test_list_playlists_normalizes_items(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'data': {
            'has_next': 1,
            'special_list': [
                {
                    'global_collection_id': 'collection-demo',
                    'specialname': 'Demo Playlist',
                    'flexible_cover': 'http://img.example.test/{size}/playlist.jpg',
                    'intro': 'Demo intro',
                    'nickname': 'Demo Creator',
                    'play_count': 10,
                    'collectcount': 20,
                    'tags': [{'tag_name': 'Pop'}, {'tag_name': 'ACG'}],
                }
            ],
        }
    }

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: _FakeClient(calls, payload))

    result = music_service.list_playlists(1, 0, 1, 12)

    assert result == {
        'items': [
            {
                'id': 'collection-demo',
                'name': 'Demo Playlist',
                'cover': 'http://img.example.test/240/playlist.jpg',
                'intro': 'Demo intro',
                'creator': 'Demo Creator',
                'play_count': 10,
                'collect_count': 20,
                'tags': ['Pop', 'ACG'],
                'list_create_userid': '',
                'list_create_listid': '',
                'list_create_gid': 'collection-demo',
            }
        ],
        'page': 1,
        'page_size': 12,
        'has_more': True,
    }
    assert calls[0]['url'] == 'http://127.0.0.1:3000/top/playlist'
    assert calls[0]['params'] == {'category_id': 0, 'page': 1, 'pagesize': 12, 'withsong': 0}


def test_get_playlist_tracks_normalizes_items(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'data': {
            'count': 1,
            'songs': [
                {
                    'name': 'Singer A、Singer B - Playlist Song.mp3',
                    'mixsongid': 321,
                    'hash': 'PLHASH',
                    'album_id': 654,
                    'timelen': 181000,
                    'cover': 'http://img.example.test/{size}/song.jpg',
                    'albuminfo': {'name': 'Playlist Album'},
                    'singerinfo': [{'name': 'Singer A'}, {'name': 'Singer B'}],
                }
            ],
        }
    }

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: _FakeClient(calls, payload))

    result = music_service.get_playlist_tracks(1, 'collection-demo', 3, 15)

    assert result['total'] == 1
    assert result['items'][0] == {
        'id': '321',
        'title': 'Playlist Song',
        'artist': 'Singer A、Singer B',
        'album': 'Playlist Album',
        'hash': 'PLHASH',
        'album_id': '654',
        'album_audio_id': '321',
        'duration': 181,
        'cover': 'http://img.example.test/240/song.jpg',
    }
    assert calls[0]['url'] == 'http://127.0.0.1:3000/playlist/track/all'
    assert calls[0]['params'] == {'id': 'collection-demo', 'page': 3, 'pagesize': 15}


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


def test_list_user_playlists_normalizes_kugou_response(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'data': {
            'total': 1,
            'info': [
                {
                    'listid': 10,
                    'name': '我喜欢',
                    'pic': 'http://img.example.test/{size}/playlist.jpg',
                    'count': 20,
                    'userid': 42,
                    'gid': 'gid-1',
                }
            ],
        }
    }

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: _FakeClient(calls, payload))

    result = music_service.list_user_playlists(1, 1, 30)

    assert result['items'][0] == {
        'id': '10',
        'name': '我喜欢',
        'cover': 'http://img.example.test/240/playlist.jpg',
        'song_count': 20,
        'is_default': False,
        'is_collected': False,
        'list_create_userid': '42',
        'list_create_listid': '10',
        'list_create_gid': 'gid-1',
    }
    assert calls[0]['url'] == 'http://127.0.0.1:3000/user/playlist'
    assert calls[0]['params'] == {'page': 1, 'pagesize': 30}


def test_get_user_playlist_tracks_includes_file_id(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'data': {
            'total': 1,
            'info': [
                {
                    'fileid': 99,
                    'name': 'Liked Song',
                    'hash': 'HASH',
                    'album_id': 1,
                    'mixsongid': 2,
                    'timelen': 180000,
                }
            ],
        }
    }

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: _FakeClient(calls, payload))

    result = music_service.get_user_playlist_tracks(1, '10', 1, 30)

    assert result['items'][0]['file_id'] == '99'
    assert result['items'][0]['hash'] == 'HASH'
    assert calls[0]['url'] == 'http://127.0.0.1:3000/playlist/track/all/new'
    assert calls[0]['params'] == {'listid': '10', 'page': 1, 'pagesize': 30}


def test_add_track_to_user_playlist_formats_track_data(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {'status': 1}

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: _FakeClient(calls, payload))

    result = music_service.add_track_to_user_playlist(
        1,
        '10',
        music_service.MusicTrackPayload(title='Song', hash='HASH', album_id='1', album_audio_id='2'),
    )

    assert result['ok'] is True
    assert calls[0]['url'] == 'http://127.0.0.1:3000/playlist/tracks/add'
    assert calls[0]['params'] == {'listid': '10', 'data': 'Song|HASH|1|2'}


def test_create_and_delete_user_playlist_use_kugou_endpoints(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payloads = [
        {'status': 1},
        {'status': 1},
    ]

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: client)

    created = music_service.create_user_playlist(1, 'New List', True)
    deleted = music_service.delete_user_playlist(1, '10')

    assert created['ok'] is True
    assert deleted['ok'] is True
    assert calls[0]['url'] == 'http://127.0.0.1:3000/playlist/add'
    assert calls[0]['params'] == {'name': 'New List', 'type': 0, 'is_pri': 1}
    assert calls[1]['url'] == 'http://127.0.0.1:3000/playlist/del'
    assert calls[1]['params'] == {'listid': '10'}


def test_collect_playlist_loads_detail_before_add(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payloads = [
        {
            'data': [
                {
                    'name': 'Public List',
                    'source': 1,
                    'list_create_userid': 42,
                    'list_create_listid': 88,
                    'list_create_gid': 'collection_3_42_88_0',
                }
            ]
        },
        {'status': 1},
    ]

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: client)

    result = music_service.collect_playlist(1, 'collection_3_42_88_0')

    assert result['ok'] is True
    assert calls[0]['url'] == 'http://127.0.0.1:3000/playlist/detail'
    assert calls[0]['params'] == {'ids': 'collection_3_42_88_0'}
    assert calls[1]['url'] == 'http://127.0.0.1:3000/playlist/add'
    assert calls[1]['params'] == {
        'name': 'Public List',
        'type': 1,
        'source': 1,
        'list_create_userid': '42',
        'list_create_listid': '88',
        'list_create_gid': 'collection_3_42_88_0',
    }


def test_user_history_and_playhistory_upload_use_kugou_endpoints(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payloads = [
        {'data': {'bp': 'next-bp', 'songs': [{'name': 'Recent Song', 'hash': 'HASH'}]}},
        {'status': 1},
    ]

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: client)

    history = music_service.get_user_history(1, None)
    report = music_service.upload_play_history(1, '123', 1710000000, 1)

    assert history['bp'] == 'next-bp'
    assert history['items'][0]['hash'] == 'HASH'
    assert report['ok'] is True
    assert calls[0]['url'] == 'http://127.0.0.1:3000/user/history'
    assert calls[0]['params'] == {}
    assert calls[1]['url'] == 'http://127.0.0.1:3000/playhistory/upload'
    assert calls[1]['params'] == {'mxid': '123', 'pc': 1, 'time': 1710000000}


def test_get_favorite_counts_uses_public_endpoint_without_auth(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'errcode': 0,
        'data': {'list': [{'mixsongid': 368015985, 'count': 376527, 'count_text': '37w'}]},
    }

    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_service.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_service, 'redis_client', redis)
    monkeypatch.setattr(music_service.httpx, 'Client', lambda **_kwargs: _FakeClient(calls, payload))

    result = music_service.get_favorite_counts(1, '368015985')

    assert result['items'] == [{'mixsongid': '368015985', 'count': 376527, 'count_text': '37w'}]
    assert calls[0]['url'] == 'http://127.0.0.1:3000/favorite/count'
    assert calls[0]['params'] == {'mixsongids': '368015985'}
    assert calls[0]['headers'] == {}
