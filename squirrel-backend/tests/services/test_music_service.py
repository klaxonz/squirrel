import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services import music as music_service
from services.music import _client as music_client

pytestmark = [pytest.mark.anyio(backend='asyncio')]


@pytest.fixture(autouse=True)
def reset_music_http_client(monkeypatch):
    monkeypatch.setattr(music_client, '_http_client', None)


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
        self.is_closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None, headers=None):
        self._calls.append({'url': url, 'params': params, 'headers': headers})
        return _FakeResponse(self._payload)


class _SequenceClient:
    def __init__(self, calls, payloads):
        self._calls = calls
        self._payloads = list(payloads)
        self.is_closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None, headers=None):
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


async def test_search_tracks_normalizes_kugou_response(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'data': {
            'total': 1,
            'lists': [
                {
                    'AlbumAudioID': 123,
                    'FileHash': 'ABC',
                    'SongName': 'Demo Artist - Demo Song',
                    'SingerName': 'Demo Artist',
                    'AlbumName': 'Demo Album',
                    'AlbumID': 456,
                    'Duration': 210,
                    'Image': 'https://img.example.test/cover.jpg',
                }
            ],
        }
    }

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    result = await music_service.search_tracks(1, 'demo', 1, 20)

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


async def test_get_personal_fm_tracks_normalizes_items(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'data': {
            'song_list': [
                {
                    'songname': 'FM Artist - FM Song.mp3',
                    'author_name': 'FM Artist',
                    'album_name': 'FM Album',
                    'album_id': 456,
                    'album_audio_id': 123,
                    'hash': 'FMHASH',
                    'time_length': 217,
                    'sizable_cover': 'http://img.example.test/{size}/fm.jpg',
                    'singerinfo': [{'id': 789, 'name': 'FM Artist'}],
                }
            ]
        }
    }

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    result = await music_service.get_personal_fm_tracks(1)

    assert result == {
        'items': [
            {
                'id': '123',
                'title': 'FM Song',
                'artist': 'FM Artist',
                'album': 'FM Album',
                'hash': 'FMHASH',
                'album_id': '456',
                'album_audio_id': '123',
                'duration': 217,
                'cover': 'http://img.example.test/240/fm.jpg',
                'artist_id': '789',
            }
        ],
        'page': 1,
        'page_size': 1,
        'total': 1,
    }
    assert calls == [
        {
            'url': 'http://127.0.0.1:3000/personal/fm',
            'params': {'mode': 'normal'},
            'headers': {'Authorization': 'token=abc;userid=1;dfid=xyz'},
        }
    ]


async def test_search_artists_normalizes_kugou_response(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'data': {
            'total': 1,
            'lists': [
                {
                    'AuthorId': 420,
                    'AuthorName': 'Demo Artist',
                    'Avatar': 'http://img.example.test/artist.jpg',
                    'AudioCount': 20,
                    'AlbumCount': 3,
                    'FansNum': 99,
                }
            ],
        }
    }

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    result = await music_service.search_artists(1, 'demo', 1, 6)

    assert result['items'] == [
        {
            'id': '420',
            'name': 'Demo Artist',
            'avatar': 'http://img.example.test/artist.jpg',
            'intro': '',
            'song_count': 20,
            'album_count': 3,
            'fan_count': 99,
        }
    ]
    assert calls[0]['params'] == {'keywords': 'demo', 'page': 1, 'pagesize': 6, 'type': 'author'}


async def test_search_albums_derives_unique_albums_from_song_results(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'data': {
            'total': 2,
            'lists': [
                {
                    'AlbumID': 1,
                    'AlbumName': 'Album A',
                    'SingerName': 'Singer A',
                    'Image': 'http://img.example.test/album-a.jpg',
                },
                {
                    'AlbumID': 1,
                    'AlbumName': 'Album A',
                    'SingerName': 'Singer A',
                    'Image': 'http://img.example.test/album-a-duplicate.jpg',
                },
                {
                    'AlbumID': 2,
                    'AlbumName': 'Album B',
                    'SingerName': 'Singer B',
                    'Image': 'http://img.example.test/album-b.jpg',
                },
            ],
        }
    }

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    result = await music_service.search_albums(1, 'demo', 1, 8)

    assert result['items'] == [
        {
            'id': '1',
            'name': 'Album A',
            'cover': 'http://img.example.test/album-a.jpg',
            'intro': '',
            'artist': 'Singer A',
            'artist_id': '',
            'publish_date': '',
            'language': '',
            'type': '',
            'heat': 0,
        },
        {
            'id': '2',
            'name': 'Album B',
            'cover': 'http://img.example.test/album-b.jpg',
            'intro': '',
            'artist': 'Singer B',
            'artist_id': '',
            'publish_date': '',
            'language': '',
            'type': '',
            'heat': 0,
        },
    ]
    assert calls[0]['params'] == {'keywords': 'demo', 'page': 1, 'pagesize': 24, 'type': 'song'}


async def test_complex_search_uses_typed_search_results(monkeypatch):
    from services.music import discovery

    calls = []

    async def fake_request(path, params, *, user_id=None, use_auth=True):
        calls.append({'path': path, 'params': params, 'user_id': user_id, 'use_auth': use_auth})
        if params['type'] == 'song':
            return {
                'data': {
                    'lists': [
                        {
                            'AlbumAudioID': 123,
                            'FileHash': 'ABC',
                            'SongName': 'Demo Artist - Demo Song',
                            'SingerName': 'Demo Artist',
                            'AlbumName': 'Demo Album',
                            'AlbumID': 456,
                            'Duration': 210,
                            'Image': 'https://img.example.test/cover.jpg',
                        }
                    ],
                },
            }
        return {
            'data': {
                'lists': [
                    {
                        'AuthorId': 420,
                        'AuthorName': 'Demo Artist',
                        'Avatar': 'http://img.example.test/artist.jpg',
                        'AudioCount': 20,
                    }
                ],
            },
        }

    monkeypatch.setattr(discovery, '_request_kugou', fake_request)

    result = await music_service.get_complex_search(1, 'demo')

    assert result['songs'][0]['title'] == 'Demo Song'
    assert result['artists'][0]['name'] == 'Demo Artist'
    assert result['albums'][0]['name'] == 'Demo Album'
    assert sorted(calls, key=lambda item: item['params']['type']) == [
        {
            'path': '/search',
            'params': {'keywords': 'demo', 'page': 1, 'pagesize': 12, 'type': 'author'},
            'user_id': 1,
            'use_auth': True,
        },
        {
            'path': '/search',
            'params': {'keywords': 'demo', 'page': 1, 'pagesize': 50, 'type': 'song'},
            'user_id': 1,
            'use_auth': True,
        },
    ]


async def test_get_track_play_url_returns_direct_url(monkeypatch):
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

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    result = await music_service.get_track_play_url(1, 'ABC', '123', '128')

    assert result['url'] == 'https://cdn.example.test/demo.mp3'
    assert result['expires_at'] == 1800
    assert calls[0]['url'] == 'http://127.0.0.1:3000/song/url'
    assert calls[0]['params'] == {'hash': 'ABC', 'quality': '128', 'album_audio_id': '123'}
    assert calls[0]['headers'] == {}


async def test_get_track_play_url_returns_string_url(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'bitRate': 128000,
        'url': 'https://cdn.example.test/demo.mp3',
    }

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    result = await music_service.get_track_play_url(1, 'ABC', '123', '128')

    assert result['url'] == 'https://cdn.example.test/demo.mp3'


async def test_get_track_lyric_returns_timed_lines(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payloads = [
        {'status': 200, 'candidates': [{'id': 'lyric-1', 'accesskey': 'access-1'}]},
        {'status': 200, 'decodeContent': '[00:01.00]First line\n[00:03.50][00:04.00]Repeat line\n[ti:Demo]'},
    ]

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: client)

    result = await music_service.get_track_lyric(1, 'Demo Song', 'Demo Artist', 'ABC', '123', 210)

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


async def test_list_ranks_normalizes_items(monkeypatch):
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

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    result = await music_service.list_ranks(1)

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


async def test_get_rank_tracks_normalizes_items(monkeypatch):
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

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    result = await music_service.get_rank_tracks(1, '8888', '115390', 2, 10)

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


async def test_list_playlists_normalizes_items(monkeypatch):
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

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    result = await music_service.list_playlists(1, 0, 1, 12)

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


async def test_search_discovery_endpoints_normalize_items(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payloads = [
        {'data': {'keyword': 'Default Song'}},
        {'data': {'info': [{'keyword': 'Hot Song', 'score': 100}]}},
        {'data': {'info': [{'keyword': 'Suggest Song', 'type': 'song'}]}},
    ]

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: client)

    default = await music_service.get_default_search_keyword(1)
    hot = await music_service.list_hot_searches(1)
    suggestions = await music_service.search_suggestions(1, 'demo')

    assert default['keyword'] == 'Default Song'
    assert hot['items'] == [{'keyword': 'Hot Song', 'score': 100, 'jump_url': ''}]
    assert suggestions['items'] == [{'keyword': 'Suggest Song', 'type': 'song'}]
    assert calls[0]['url'] == 'http://127.0.0.1:3000/search/default'
    assert calls[1]['url'] == 'http://127.0.0.1:3000/search/hot'
    assert calls[2]['url'] == 'http://127.0.0.1:3000/search/suggest'
    assert calls[2]['params']['keywords'] == 'demo'


async def test_recommend_discovery_cards_normalize_tracks(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payloads = [
        {
            'data': {
                'rec_desc': '「精选好歌随心听」',
                'song_list_size': 2,
                'song_list': [
                    {
                        'songname': 'Card Song',
                        'author_name': 'Card Singer',
                        'hash': 'CARDHASH',
                        'album_audio_id': 123,
                        'album_id': 456,
                        'time_length': 180,
                        'sizable_cover': 'http://img.example.test/{size}/card.jpg',
                    }
                ],
            }
        },
        {
            'data': {
                'song_list_size': 1,
                'cover_img_url': 'http://img.example.test/{size}/daily.jpg',
                'song_list': [
                    {
                        'songname': 'Daily Song',
                        'author_name': 'Daily Singer',
                        'hash': 'DAILYHASH',
                        'album_audio_id': 789,
                        'album_id': 987,
                        'time_length': 210,
                    }
                ],
            }
        },
    ]

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: client)

    card = await music_service.get_recommend_card_tracks(1, 1, 8)
    daily = await music_service.get_daily_recommend_tracks(1, 6)

    assert card['title'] == '精选好歌随心听'
    assert card['card_id'] == 1
    assert card['items'][0]['title'] == 'Card Song'
    assert card['items'][0]['cover'] == 'http://img.example.test/240/card.jpg'
    assert daily['cover'] == 'http://img.example.test/240/daily.jpg'
    assert daily['items'][0]['title'] == 'Daily Song'
    assert calls[0]['url'] == 'http://127.0.0.1:3000/top/card'
    assert calls[0]['params'] == {'card_id': 1}
    assert calls[1]['url'] == 'http://127.0.0.1:3000/recommend/songs'


async def test_playlist_tags_and_similar_playlists_normalize_items(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payloads = [
        {
            'data': {
                'info': [
                    {
                        'tag_name': 'Language',
                        'children': [{'tag_id': 123, 'tag_name': 'Mandarin'}],
                    }
                ]
            }
        },
        {
            'data': {
                'list': [
                    {
                        'global_collection_id': 'collection-similar',
                        'specialname': 'Similar Playlist',
                        'imgurl': 'http://img.example.test/{size}/playlist.jpg',
                    }
                ]
            }
        },
    ]

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: client)

    tags = await music_service.list_playlist_tags(1)
    similar = await music_service.get_similar_playlists(1, 'collection-demo')

    assert tags['items'] == [{'id': '123', 'name': 'Mandarin', 'parent_name': 'Language'}]
    assert similar['items'][0]['id'] == 'collection-similar'
    assert similar['items'][0]['cover'] == 'http://img.example.test/240/playlist.jpg'
    assert calls[0]['url'] == 'http://127.0.0.1:3000/playlist/tags'
    assert calls[1]['url'] == 'http://127.0.0.1:3000/playlist/similar'
    assert calls[1]['params'] == {'ids': 'collection-demo'}


async def test_get_playlist_tracks_normalizes_items(monkeypatch):
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
                    'albuminfo': {
                        'name': 'Playlist Album',
                        'sizable_cover': 'http://img.example.test/{size}/song.jpg',
                    },
                    'singerinfo': [{'name': 'Singer A'}, {'name': 'Singer B'}],
                }
            ],
        }
    }

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    result = await music_service.get_playlist_tracks(1, 'collection-demo', 3, 15)

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


async def test_get_artist_detail_and_tracks_normalize_items(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payloads = [
        {
            'data': {
                'author_id': 10,
                'author_name': 'Singer A',
                'sizable_avatar': 'http://img.example.test/{size}/artist.jpg',
                'intro': 'Artist intro',
                'song_count': 2,
                'album_count': 1,
                'fansnums': 99,
            }
        },
        {
            'total': 1,
            'data': [
                {
                    'audio_name': 'Artist Song',
                    'author_name': 'Singer A',
                    'author_id': 10,
                    'album_name': 'Artist Album',
                    'album_id': 20,
                    'album_audio_id': 30,
                    'hash': 'ARTHASH',
                    'timelength_128': 123000,
                    'trans_param': {'union_cover': 'http://img.example.test/{size}/song.jpg'},
                }
            ],
        },
    ]

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: client)

    detail = await music_service.get_artist_detail(1, '10')
    tracks = await music_service.get_artist_tracks(1, '10', 2, 30)

    assert detail == {
        'id': '10',
        'name': 'Singer A',
        'avatar': 'http://img.example.test/240/artist.jpg',
        'intro': 'Artist intro',
        'song_count': 2,
        'album_count': 1,
        'fan_count': 99,
    }
    assert tracks['items'][0] == {
        'id': '30',
        'title': 'Artist Song',
        'artist': 'Singer A',
        'artist_id': '10',
        'album': 'Artist Album',
        'hash': 'ARTHASH',
        'album_id': '20',
        'album_audio_id': '30',
        'duration': 123,
        'cover': 'http://img.example.test/240/song.jpg',
    }
    assert calls[0]['url'] == 'http://127.0.0.1:3000/artist/detail'
    assert calls[0]['params'] == {'id': '10'}
    assert calls[1]['url'] == 'http://127.0.0.1:3000/artist/audios'
    assert calls[1]['params'] == {'id': '10', 'page': 2, 'pagesize': 30}


async def test_get_album_detail_and_tracks_normalize_items(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payloads = [
        {
            'data': [
                {
                    'album_id': 20,
                    'album_name': 'Album A',
                    'sizable_cover': 'http://img.example.test/{size}/album.jpg',
                    'intro': 'Album intro',
                    'author_name': 'Singer A',
                    'publish_date': '2026-01-01',
                    'language': '国语',
                    'type': '录音室专辑',
                    'heat': '12',
                    'authors': [{'author_id': 10, 'author_name': 'Singer A'}],
                }
            ]
        },
        {
            'data': {
                'total': 1,
                'songs': [
                    {
                        'base': {
                            'audio_name': 'Album Song',
                            'author_name': 'Singer A',
                            'album_id': 20,
                            'album_audio_id': 30,
                        },
                        'authors': [{'author_id': 10, 'author_name': 'Singer A'}],
                        'audio_info': {'hash': 'ALBHASH', 'duration': 210000},
                        'album_info': {
                            'album_name': 'Album A',
                            'cover': 'http://img.example.test/{size}/album.jpg',
                        },
                    }
                ],
            }
        },
    ]

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: client)

    detail = await music_service.get_album_detail(1, '20')
    tracks = await music_service.get_album_tracks(1, '20', 1, 30)

    assert detail == {
        'id': '20',
        'name': 'Album A',
        'cover': 'http://img.example.test/240/album.jpg',
        'intro': 'Album intro',
        'artist': 'Singer A',
        'artist_id': '10',
        'publish_date': '2026-01-01',
        'language': '国语',
        'type': '录音室专辑',
        'heat': 12,
    }
    assert tracks['items'][0] == {
        'id': '30',
        'title': 'Album Song',
        'artist': 'Singer A',
        'artist_id': '10',
        'album': 'Album A',
        'hash': 'ALBHASH',
        'album_id': '20',
        'album_audio_id': '30',
        'duration': 210,
        'cover': 'http://img.example.test/240/album.jpg',
    }
    assert calls[0]['url'] == 'http://127.0.0.1:3000/album/detail'
    assert calls[0]['params'] == {'id': '20'}
    assert calls[1]['url'] == 'http://127.0.0.1:3000/album/songs'
    assert calls[1]['params'] == {'id': '20', 'page': 1, 'pagesize': 30}


async def test_new_songs_normalize_items(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'data': {
            'total': 1,
            'songs': [
                {
                    'audio_name': 'New Song',
                    'author_name': 'Singer A',
                    'album_audio_id': 30,
                    'hash': 'NEWHASH',
                }
            ],
        }
    }

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    songs = await music_service.list_new_songs(1, None, 1, 30)

    assert songs['items'][0]['title'] == 'New Song'
    assert calls[0]['url'] == 'http://127.0.0.1:3000/top/song'


async def test_new_albums_collect_all_regions(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'data': {
            'chn': [
                {'album_id': 1, 'album_name': 'CN Album 1', 'author_name': 'Singer A'},
                {'album_id': 2, 'album_name': 'CN Album 2', 'author_name': 'Singer B'},
                {'album_id': 3, 'album_name': 'CN Album 3', 'author_name': 'Singer C'},
            ],
            'eur': [{'album_id': 4, 'album_name': 'EU Album', 'author_name': 'Singer D'}],
            'jpn': [{'album_id': 5, 'album_name': 'JP Album', 'author_name': 'Singer E'}],
            'kor': [{'album_id': 6, 'album_name': 'KR Album', 'author_name': 'Singer F'}],
        }
    }

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    albums = await music_service.list_new_albums(1, 1, 30)

    assert [item['name'] for item in albums['items']] == [
        'CN Album 1',
        'CN Album 2',
        'CN Album 3',
        'EU Album',
        'JP Album',
        'KR Album',
    ]
    assert albums['total'] == 6
    assert calls[0]['url'] == 'http://127.0.0.1:3000/top/album'
    assert calls[0]['params'] == {}


async def test_new_albums_slice_requested_page(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'data': {
            'chn': [
                {'album_id': 1, 'album_name': 'Album 1'},
                {'album_id': 2, 'album_name': 'Album 2'},
                {'album_id': 3, 'album_name': 'Album 3'},
                {'album_id': 4, 'album_name': 'Album 4'},
            ],
            'eur': [],
            'jpn': [],
            'kor': [],
        }
    }

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    albums = await music_service.list_new_albums(1, 2, 2)

    assert [item['name'] for item in albums['items']] == ['Album 3', 'Album 4']
    assert albums['page'] == 2
    assert albums['page_size'] == 2
    assert calls[0]['params'] == {}


async def test_track_enrichment_endpoints_normalize_items(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payloads = [
        {'data': [{'hash': 'HASH', 'start': 45, 'duration': 20}]},
        {
            'data': {
                'total': 1,
                'list': [
                    {
                        'audio_name': 'Related Song',
                        'author_name': 'Singer A',
                        'album_audio_id': 30,
                        'hash': 'RELHASH',
                    }
                ],
            }
        },
        {
            'data': {
                'list': [
                    {
                        'video_id': 99,
                        'title': 'Demo MV',
                        'hash': 'MVHASH',
                        'cover': 'http://img.example.test/{size}/mv.jpg',
                    }
                ]
            }
        },
    ]

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: client)

    climax = await music_service.get_track_climax(1, 'HASH')
    related = await music_service.get_related_tracks(1, '30', 1, 30, 'all', None)
    mv = await music_service.get_track_mv(1, '30')

    assert climax['items'] == [{'hash': 'HASH', 'start': 45, 'duration': 20}]
    assert related['items'][0]['title'] == 'Related Song'
    assert mv['items'][0]['name'] == 'Demo MV'
    assert calls[0]['url'] == 'http://127.0.0.1:3000/song/climax'
    assert calls[1]['url'] == 'http://127.0.0.1:3000/audio/related'
    assert calls[2]['url'] == 'http://127.0.0.1:3000/kmr/audio/mv'


async def test_request_requires_configured_base_url(monkeypatch):
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', '')
    monkeypatch.setattr(music_client, 'redis_client', _FakeRedis())

    try:
        await music_service.search_tracks(1, 'demo', 1, 20)
    except music_service.MusicServiceError as exc:
        assert str(exc) == 'KUGOU_MUSIC_API_BASE_URL is not configured'
    else:
        raise AssertionError('MusicServiceError was not raised')


async def test_request_reports_non_json_response(monkeypatch):
    calls = []
    redis = _FakeRedis()

    class _InvalidJsonClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None, headers=None):
            calls.append({'url': url, 'params': params, 'headers': headers})
            return _InvalidJsonResponse()

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _InvalidJsonClient())

    try:
        await music_service.search_tracks(1, 'demo', 1, 20)
    except music_service.MusicServiceError as exc:
        message = str(exc)
        assert 'KuGouMusicApi returned non-JSON response' in message
        assert 'content_type=text/html; charset=utf-8' in message
        assert 'Not an API' in message
    else:
        raise AssertionError('MusicServiceError was not raised')


async def test_create_qr_login_returns_key_and_image(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payloads = [
        {'data': {'qrcode': 'qr-demo'}},
        {'data': {'url': 'https://h5.kugou.com/login?qrcode=qr-demo', 'base64': 'data:image/png;base64,abc'}},
    ]

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: client)

    result = await music_service.create_qr_login()

    assert result == {
        'key': 'qr-demo',
        'url': 'https://h5.kugou.com/login?qrcode=qr-demo',
        'base64': 'data:image/png;base64,abc',
    }
    assert calls[0]['url'] == 'http://127.0.0.1:3000/login/qr/key'
    assert calls[1]['url'] == 'http://127.0.0.1:3000/login/qr/create'
    assert calls[1]['params'] == {'key': 'qr-demo', 'qrimg': 1}


async def test_check_qr_login_saves_redis_cookie(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payloads = [
        {'data': {'status': 4, 'token': 'token-demo', 'userid': 42}},
        {'data': {'dfid': 'dfid-demo'}},
    ]

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', '')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client, '_timestamp_ms', lambda: 1000)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: client)

    result = await music_service.check_qr_login(1, 'qr-demo')

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


async def test_search_tracks_prefers_redis_cookie(monkeypatch):
    calls = []
    redis = _FakeRedis()
    redis.set('music:kugou:auth:1', 'token=redis-token;userid=9;dfid=redis-dfid')
    payload = {'data': {'total': 0, 'lists': []}}

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', 'token=env-token;userid=1;dfid=env-dfid')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    await music_service.search_tracks(1, 'demo', 1, 20)

    assert calls[0]['headers'] == {'Authorization': 'token=redis-token;userid=9;dfid=redis-dfid'}


async def test_list_user_playlists_normalizes_kugou_response(monkeypatch):
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

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    result = await music_service.list_user_playlists(1, 1, 30)

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


async def test_get_user_playlist_tracks_includes_file_id(monkeypatch):
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

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    result = await music_service.get_user_playlist_tracks(1, '10', 1, 30)

    assert result['items'][0]['file_id'] == '99'
    assert result['items'][0]['hash'] == 'HASH'
    assert calls[0]['url'] == 'http://127.0.0.1:3000/playlist/track/all/new'
    assert calls[0]['params'] == {'listid': '10', 'page': 1, 'pagesize': 30}


async def test_add_track_to_user_playlist_formats_track_data(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {'status': 1}

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    result = await music_service.add_track_to_user_playlist(
        1,
        '10',
        music_service.MusicTrackPayload(title='Song', hash='HASH', album_id='1', album_audio_id='2'),
    )

    assert result['ok'] is True
    assert calls[0]['url'] == 'http://127.0.0.1:3000/playlist/tracks/add'
    assert calls[0]['params'] == {'listid': '10', 'data': 'Song|HASH|1|2'}


async def test_create_and_delete_user_playlist_use_kugou_endpoints(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payloads = [
        {'status': 1},
        {'status': 1},
    ]

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: client)

    created = await music_service.create_user_playlist(1, 'New List', True)
    deleted = await music_service.delete_user_playlist(1, '10')

    assert created['ok'] is True
    assert deleted['ok'] is True
    assert calls[0]['url'] == 'http://127.0.0.1:3000/playlist/add'
    assert calls[0]['params'] == {'name': 'New List', 'type': 0, 'is_pri': 1}
    assert calls[1]['url'] == 'http://127.0.0.1:3000/playlist/del'
    assert calls[1]['params'] == {'listid': '10'}


async def test_collect_playlist_loads_detail_before_add(monkeypatch):
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

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: client)

    result = await music_service.collect_playlist(1, 'collection_3_42_88_0')

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


async def test_user_history_and_playhistory_upload_use_kugou_endpoints(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payloads = [
        {'data': {'bp': 'next-bp', 'songs': [{'name': 'Recent Song', 'hash': 'HASH'}]}},
        {'status': 1},
    ]

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    client = _SequenceClient(calls, payloads)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: client)

    history = await music_service.get_user_history(1, None)
    report = await music_service.upload_play_history(1, '123', 1710000000, 1)

    assert history['bp'] == 'next-bp'
    assert history['items'][0]['hash'] == 'HASH'
    assert report['ok'] is True
    assert calls[0]['url'] == 'http://127.0.0.1:3000/user/history'
    assert calls[0]['params'] == {}
    assert calls[1]['url'] == 'http://127.0.0.1:3000/playhistory/upload'
    assert calls[1]['params'] == {'mxid': '123', 'pc': 1, 'time': 1710000000}


async def test_get_favorite_counts_uses_public_endpoint_without_auth(monkeypatch):
    calls = []
    redis = _FakeRedis()
    payload = {
        'errcode': 0,
        'data': {'list': [{'mixsongid': 368015985, 'count': 376527, 'count_text': '37w'}]},
    }

    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_API_BASE_URL', 'http://127.0.0.1:3000')
    monkeypatch.setattr(music_client.settings, 'KUGOU_MUSIC_COOKIE', 'token=abc;userid=1;dfid=xyz')
    monkeypatch.setattr(music_client, 'redis_client', redis)
    monkeypatch.setattr(music_client.httpx, 'AsyncClient', lambda **_kwargs: _FakeClient(calls, payload))

    result = await music_service.get_favorite_counts(1, '368015985')

    assert result['items'] == [{'mixsongid': '368015985', 'count': 376527, 'count_text': '37w'}]
    assert calls[0]['url'] == 'http://127.0.0.1:3000/favorite/count'
    assert calls[0]['params'] == {'mixsongids': '368015985'}
    assert calls[0]['headers'] == {}
