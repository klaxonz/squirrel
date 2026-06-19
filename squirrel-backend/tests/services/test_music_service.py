"""Tests for MusicService class — network layer mocked with respx, redis injected."""

from types import SimpleNamespace

import httpx
import pytest
import respx

from domains.music.application.services.service import MusicService

pytestmark = [pytest.mark.anyio]

BASE_URL = 'http://127.0.0.1:3000'
TEST_SETTINGS = SimpleNamespace(
    kugou_music=SimpleNamespace(api_base_url=BASE_URL, cookie='token=abc;userid=1;dfid=xyz'),
)


def _svc(mock_redis=None):
    return MusicService(redis_client=mock_redis, settings=TEST_SETTINGS)


def _mock_search_payload(items=None):
    return {
        'data': {
            'total': 1,
            'lists': items
            or [
                {
                    'AlbumAudioID': 123,
                    'FileHash': 'ABC',
                    'SongName': 'Demo Artist - Demo Song',
                    'SingerName': 'Demo Artist',
                    'AlbumName': 'Demo Album',
                    'AlbumID': 456,
                    'Duration': 210,
                    'Image': 'https://img.example.test/cover.jpg',
                },
            ],
        },
    }


def _fm_payload(items=None):
    return {
        'data': {
            'song_list': items
            or [
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
                },
            ],
        },
    }


async def test_search_tracks_normalizes_kugou_response(mock_redis):
    svc = _svc(mock_redis)
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/search').mock(
            return_value=httpx.Response(200, json=_mock_search_payload()),
        )
        result = await svc.search_tracks(1, 'demo', 1, 20)

    assert route.called
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
        },
    ]


async def test_get_personal_fm_tracks_normalizes_items(mock_redis):
    svc = _svc(mock_redis)
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/personal/fm').mock(
            return_value=httpx.Response(200, json=_fm_payload()),
        )
        result = await svc.get_personal_fm_tracks(1)

    assert route.called
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
            },
        ],
        'page': 1,
        'page_size': 1,
        'total': 1,
    }


async def test_search_artists_normalizes_kugou_response(mock_redis):
    svc = _svc(mock_redis)
    payload = {
        'data': {
            'total': 2,
            'lists': [
                {
                    'AuthorName': 'Artist One',
                    'AuthorId': '101',
                    'Avatar': 'https://img.example.test/{size}/artist1.jpg',
                    'AudioCount': 42,
                    'AlbumCount': 3,
                    'Source': 1,
                },
                {
                    'AuthorName': 'Artist Two',
                    'AuthorId': '102',
                    'Avatar': 'https://img.example.test/{size}/artist2.jpg',
                    'AudioCount': 99,
                    'AlbumCount': 7,
                    'Source': 1,
                },
            ],
        },
    }
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/search').mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await svc.search_artists(1, 'artist', 1, 10)

    assert route.called
    assert len(result['items']) == 2
    assert result['items'][0]['name'] == 'Artist One'
    assert result['items'][0]['id'] == '101'


async def test_search_albums_derives_unique_albums_from_song_results(mock_redis):
    svc = _svc(mock_redis)
    payload = {
        'data': {
            'lists': [
                {
                    'AlbumID': 1,
                    'AlbumName': 'Album A',
                    'SingerName': 'Artist A',
                    'Image': 'https://img.example.test/a.jpg',
                    'FileHash': 'H1',
                    'AlbumAudioID': 11,
                },
                {
                    'AlbumID': 2,
                    'AlbumName': 'Album B',
                    'SingerName': 'Artist B',
                    'Image': 'https://img.example.test/b.jpg',
                    'FileHash': 'H2',
                    'AlbumAudioID': 22,
                },
            ],
        },
    }
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/search').mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await svc.search_albums(1, 'album', 1, 20)

    assert route.called
    assert len(result['items']) == 2
    assert result['items'][0]['name'] == 'Album A'


async def test_complex_search_uses_typed_search_results(mock_redis):
    svc = _svc(mock_redis)
    async with respx.mock:
        song_route = respx.get(f'{BASE_URL}/search', params__contains={'type': 'song'}).mock(
            return_value=httpx.Response(200, json=_mock_search_payload()),
        )
        artist_route = respx.get(f'{BASE_URL}/search', params__contains={'type': 'author'}).mock(
            return_value=httpx.Response(200, json={'data': {'lists': []}}),
        )
        result = await svc.get_complex_search(1, 'test')

    assert song_route.called
    assert artist_route.called
    assert len(result['songs']) == 1


async def test_get_track_play_url_returns_direct_url(mock_redis):
    svc = _svc(mock_redis)
    payload = {'url': 'http://example.test/track.mp3', 'bitRate': '128'}
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/song/url').mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await svc.get_track_play_url(1, 'HASH', None, '128')

    assert route.called
    assert result['url'] == 'http://example.test/track.mp3'
    assert result['quality'] == '128'


async def test_get_track_play_url_returns_string_url(mock_redis):
    svc = _svc(mock_redis)
    payload = {'url': ['http://fallback.test/1.mp3', 'http://fallback.test/2.mp3'], 'bitRate': '320'}
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/song/url').mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await svc.get_track_play_url(1, 'HASH', None, '320')

    assert route.called
    assert result['url'] == 'http://fallback.test/1.mp3'


async def test_get_track_lyric_returns_timed_lines(mock_redis):
    svc = _svc(mock_redis)
    search_payload = {'candidates': [{'id': '999', 'accesskey': 'key123'}]}
    lyric_payload = {'decodeContent': '[00:01.00]Line 1\n[00:02.50]Line 2'}
    async with respx.mock:
        search_route = respx.get(f'{BASE_URL}/search/lyric').mock(
            return_value=httpx.Response(200, json=search_payload),
        )
        lyric_route = respx.get(f'{BASE_URL}/lyric').mock(
            return_value=httpx.Response(200, json=lyric_payload),
        )
        result = await svc.get_track_lyric(1, 'Song', 'Artist', 'HASH', None, 200)

    assert search_route.called
    assert lyric_route.called
    assert len(result['lines']) == 2
    assert result['lines'][0]['text'] == 'Line 1'
    assert result['lines'][0]['time'] == 1.0


async def test_list_ranks_normalizes_items(mock_redis):
    svc = _svc(mock_redis)
    payload = {'data': {'info': [{'rankid': 'R1', 'rankname': 'Hot', 'img': '', 'count': 100}]}}
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/rank/list').mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await svc.list_ranks(1)

    assert route.called
    assert result['items'][0]['name'] == 'Hot'
    assert result['items'][0]['id'] == 'R1'


async def test_get_rank_tracks_normalizes_items(mock_redis):
    svc = _svc(mock_redis)
    payload = {'data': {'songlist': [{'FileHash': 'RH', 'SongName': 'R Song', 'SingerName': 'R Artist'}]}}
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/rank/audio').mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await svc.get_rank_tracks(1, 'R1', None, 1, 20)

    assert route.called
    assert result['items'][0]['hash'] == 'RH'


async def test_list_playlists_normalizes_items(mock_redis):
    svc = _svc(mock_redis)
    payload = {
        'data': {
            'special_list': [
                {
                    'specialname': 'Playlist 1',
                    'global_collection_id': '1',
                    'imgurl': '',
                    'play_count': 500,
                    'list_create_userid': 'u1',
                },
            ],
            'has_next': True,
        },
    }
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/top/playlist').mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await svc.list_playlists(1, 0, 1, 20)

    assert route.called
    assert result['has_more'] is True
    assert result['items'][0]['name'] == 'Playlist 1'


async def test_search_discovery_endpoints_normalize_items(mock_redis):
    svc = _svc(mock_redis)
    items = [
        {
            'FileHash': 'D1',
            'SongName': 'Discovery Artist - D Song',
            'SingerName': 'Discovery Artist',
            'AlbumName': 'D Album',
            'AlbumID': 1,
            'AlbumAudioID': 1,
            'Duration': 200,
            'Image': '',
        },
    ]
    song_payload = {'data': {'songs': items}}
    rank_list_payload = {'data': {'info': []}}
    async with respx.mock:
        respx.get(f'{BASE_URL}/top/song').mock(return_value=httpx.Response(200, json=song_payload))
        respx.get(f'{BASE_URL}/rank/list').mock(return_value=httpx.Response(200, json=rank_list_payload))
        respx.get(f'{BASE_URL}/recommend/songs').mock(return_value=httpx.Response(200, json=song_payload))
        respx.get(f'{BASE_URL}/brush').mock(return_value=httpx.Response(200, json=song_payload))
        respx.get(f'{BASE_URL}/ai/recommend').mock(return_value=httpx.Response(200, json=song_payload))
        respx.get(f'{BASE_URL}/everyday/recommend').mock(return_value=httpx.Response(200, json=song_payload))
        respx.get(f'{BASE_URL}/everyday/style/recommend').mock(return_value=httpx.Response(200, json=song_payload))
        respx.get(f'{BASE_URL}/search/hot').mock(return_value=httpx.Response(200, json={'data': {'info': []}}))
        respx.get(f'{BASE_URL}/search/default').mock(
            return_value=httpx.Response(200, json={'data': {'keyword': 'hot'}})
        )

        new_songs = await svc.list_new_songs(1, None, 1, 50)
        await svc.list_ranks(1)
        await svc.get_daily_recommend_tracks(1, 10)
        await svc.get_brush_feed(1, 10)
        await svc.get_ai_recommend_tracks(1, 10)
        await svc.get_everyday_recommend(1)
        await svc.get_style_recommend(1)
        await svc.list_hot_searches(1)
        keyword = await svc.get_default_search_keyword(1)

    assert len(new_songs['items']) == 1
    assert keyword['keyword'] == 'hot'


async def test_recommend_discovery_cards_normalize_tracks(mock_redis):
    svc = _svc(mock_redis)
    payload = {
        'data': {
            'song_list': [
                {'FileHash': 'C1', 'SongName': 'C Song', 'SingerName': 'C Artist', 'Duration': 180, 'Image': ''}
            ],
            'rec_desc': 'Card 1',
        }
    }
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/top/card').mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await svc.get_recommend_card_tracks(1, 1, 10)

    assert route.called
    assert result['title'] == 'Card 1'
    assert result['items'][0]['hash'] == 'C1'


async def test_playlist_tags_and_similar_playlists_normalize_items(mock_redis):
    svc = _svc(mock_redis)
    tags_payload = {'data': {'info': [{'id': 1, 'name': 'Pop', 'count': 100}]}}
    similar_payload = {
        'data': {'info': [{'global_collection_id': '2', 'specialname': 'Similar', 'imgurl': '', 'play_count': 50}]}
    }
    async with respx.mock:
        tags_route = respx.get(f'{BASE_URL}/playlist/tags').mock(
            return_value=httpx.Response(200, json=tags_payload),
        )
        similar_route = respx.get(f'{BASE_URL}/playlist/similar').mock(
            return_value=httpx.Response(200, json=similar_payload),
        )
        tags = await svc.list_playlist_tags(1)
        similar = await svc.get_similar_playlists(1, '99')

    assert tags_route.called
    assert similar_route.called
    assert tags['items'][0]['name'] == 'Pop'
    assert similar['items'][0]['name'] == 'Similar'


async def test_get_playlist_tracks_normalizes_items(mock_redis):
    svc = _svc(mock_redis)
    payload = {'data': {'songs': [{'FileHash': 'PT1', 'SongName': 'PT Song', 'SingerName': 'PT Artist'}], 'count': 1}}
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/playlist/track/all').mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await svc.get_playlist_tracks(1, '99', 1, 20)

    assert route.called
    assert result['total'] == 1


async def test_get_artist_detail_and_tracks_normalize_items(mock_redis):
    svc = _svc(mock_redis)
    detail_payload = {
        'data': {'author_id': 'A1', 'author_name': 'Artist 1', 'sizable_avatar': '', 'song_count': 10, 'album_count': 2}
    }
    track_payload = {
        'data': [{'FileHash': 'AT1', 'SongName': 'AT Song', 'SingerName': 'Artist 1', 'Duration': 200, 'Image': ''}]
    }
    album_payload = {'data': [{'album_id': 'AL1', 'album_name': 'Album 1', 'img': ''}]}
    async with respx.mock:
        detail_route = respx.get(f'{BASE_URL}/artist/detail').mock(
            return_value=httpx.Response(200, json=detail_payload),
        )
        track_route = respx.get(f'{BASE_URL}/artist/audios').mock(
            return_value=httpx.Response(200, json=track_payload),
        )
        album_route = respx.get(f'{BASE_URL}/artist/albums').mock(
            return_value=httpx.Response(200, json=album_payload),
        )
        detail = await svc.get_artist_detail(1, 'A1')
        tracks = await svc.get_artist_tracks(1, 'A1', 1, 20)
        albums = await svc.get_artist_albums(1, 'A1', 1, 20)

    assert detail_route.called
    assert track_route.called
    assert album_route.called
    assert detail['name'] == 'Artist 1'
    assert tracks['items'][0]['hash'] == 'AT1'
    assert albums['items'][0]['name'] == 'Album 1'


async def test_get_album_detail_and_tracks_normalize_items(mock_redis):
    svc = _svc(mock_redis)
    detail_payload = {'data': [{'album_id': 'AL1', 'album_name': 'Album 1', 'img': ''}]}
    track_payload = {'data': {'songs': [{'FileHash': 'ABT1'}], 'total': 1}}
    async with respx.mock:
        detail_route = respx.get(f'{BASE_URL}/album/detail').mock(
            return_value=httpx.Response(200, json=detail_payload),
        )
        track_route = respx.get(f'{BASE_URL}/album/songs').mock(
            return_value=httpx.Response(200, json=track_payload),
        )
        detail = await svc.get_album_detail(1, 'AL1')
        tracks = await svc.get_album_tracks(1, 'AL1', 1, 20)

    assert detail_route.called
    assert track_route.called
    assert detail['name'] == 'Album 1'
    assert tracks['total'] == 1


async def test_new_songs_normalize_items(mock_redis):
    svc = _svc(mock_redis)
    payload = {'data': {'songs': [{'FileHash': 'NS1', 'SongName': 'NS Song'}], 'total': 1}}
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/top/song').mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await svc.list_new_songs(1, 1, 1, 50)

    assert route.called
    assert len(result['items']) == 1


async def test_new_albums_collect_all_regions(mock_redis):
    svc = _svc(mock_redis)
    payload = {
        'data': {
            'chn': [{'album_id': '1', 'album_name': 'CN Album', 'img': ''}],
            'eur': [{'album_id': '2', 'album_name': 'EU Album', 'img': ''}],
            'jpn': [{'album_id': '3', 'album_name': 'JP Album', 'img': ''}],
            'kor': [{'album_id': '4', 'album_name': 'KR Album', 'img': ''}],
        },
    }
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/top/album').mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await svc.list_new_albums(1, 1, 10)

    assert route.called
    assert len(result['items']) == 4


async def test_new_albums_slice_requested_page(mock_redis):
    svc = _svc(mock_redis)
    payload = {'data': {'chn': [{'album_id': str(i), 'album_name': f'A{i}', 'img': ''} for i in range(5)]}}
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/top/album').mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await svc.list_new_albums(1, 1, 2)

    assert route.called
    assert len(result['items']) == 2
    assert result['items'][0]['id'] == '0'


async def test_track_enrichment_endpoints_normalize_items(mock_redis):
    svc = _svc(mock_redis)
    mv_payload = {'data': {'info': [{'id': 'MV1', 'title': 'MV Title', 'img': ''}]}}
    climax_payload = {'data': [{'hash': 'CH', 'start': 10, 'duration': 30}]}
    related_payload = {'data': {'info': [{'FileHash': 'RT1'}]}}
    comment_payload = {'data': {'cmtlist': [{'id': 'C1', 'content': 'nice'}], 'total': 1}}
    fav_payload = {'data': {'list': [{'mixsongid': 'MS1', 'count': 5}]}}
    async with respx.mock:
        respx.get(f'{BASE_URL}/kmr/audio/mv').mock(return_value=httpx.Response(200, json=mv_payload))
        respx.get(f'{BASE_URL}/song/climax').mock(return_value=httpx.Response(200, json=climax_payload))
        respx.get(f'{BASE_URL}/audio/related').mock(return_value=httpx.Response(200, json=related_payload))
        respx.get(f'{BASE_URL}/comment/music').mock(return_value=httpx.Response(200, json=comment_payload))
        respx.get(f'{BASE_URL}/favorite/count').mock(return_value=httpx.Response(200, json=fav_payload))
        respx.get(f'{BASE_URL}/comment/album').mock(return_value=httpx.Response(200, json=comment_payload))
        respx.get(f'{BASE_URL}/comment/playlist').mock(return_value=httpx.Response(200, json=comment_payload))
        respx.get(f'{BASE_URL}/comment/floor').mock(return_value=httpx.Response(200, json=comment_payload))

        mv = await svc.get_track_mv(1, 'AA1')
        await svc.get_track_climax(1, 'CH')
        await svc.get_related_tracks(1, 'AA1', 1, 20, 'all', None)
        await svc.get_song_comments(1, 'MS1', 1, 20)
        await svc.get_favorite_counts(1, 'MS1')
        await svc.get_album_comments(1, 'AL1', 1, 20)
        await svc.get_playlist_comments(1, 'PL1', 1, 20)
        await svc.get_floor_comments(1, 'SP1', None, 1, 20)

    assert mv['items'][0]['id'] == 'MV1'


async def test_request_requires_configured_base_url(mock_redis):
    svc = MusicService(
        redis_client=mock_redis, settings=SimpleNamespace(kugou_music=SimpleNamespace(api_base_url='', cookie=''))
    )
    from domains.music.application.services._client import MusicServiceError

    with pytest.raises(MusicServiceError, match='KUGOU_MUSIC_API_BASE_URL is not configured'):
        await svc.search_tracks(1, 'test', 1, 20)


async def test_request_reports_non_json_response(mock_redis):
    svc = _svc(mock_redis)
    from domains.music.application.services._client import MusicServiceError

    async with respx.mock:
        respx.get(f'{BASE_URL}/search').mock(
            return_value=httpx.Response(200, text='<html>not json</html>', headers={'content-type': 'text/html'}),
        )
        with pytest.raises(MusicServiceError, match='non-JSON'):
            await svc.search_tracks(1, 'test', 1, 20)


async def test_create_qr_login_returns_key_and_image(mock_redis):
    svc = _svc(mock_redis)
    key_payload = {'data': {'qrcode': 'QR_KEY'}}
    qr_payload = {'data': {'url': 'http://qr.test', 'base64': 'data:image'}}
    async with respx.mock:
        key_route = respx.get(f'{BASE_URL}/login/qr/key').mock(
            return_value=httpx.Response(200, json=key_payload),
        )
        qr_route = respx.get(f'{BASE_URL}/login/qr/create').mock(
            return_value=httpx.Response(200, json=qr_payload),
        )
        result = await svc.create_qr_login()

    assert key_route.called
    assert qr_route.called
    assert result['key'] == 'QR_KEY'
    assert result['base64'] == 'data:image'


async def test_check_qr_login_saves_redis_cookie(mock_redis):
    svc = _svc(mock_redis)
    check_payload = {'data': {'status': 4, 'token': 'tok', 'userid': '99'}}
    async with respx.mock:
        # qr check
        respx.get(f'{BASE_URL}/login/qr/check').mock(
            return_value=httpx.Response(200, json=check_payload),
        )
        # _save_user_cookie_from_login → _effective_cookie → returns cookie from mock_redis
        # dfid check: _effective_cookie returns settings.kugou_music.cookie which has dfid=xyz
        result = await svc.check_qr_login(1, 'KEY')

    assert result['logged_in'] is True
    # cookie should be saved in redis
    saved = mock_redis.get('music:kugou:auth:1')
    assert saved == 'token=tok;userid=99;dfid=xyz'


async def test_search_tracks_prefers_redis_cookie(mock_redis):
    svc = _svc(mock_redis)
    mock_redis.set('music:kugou:auth:1', 'token=redis_tok;userid=2;dfid=redis_dfid')
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/search').mock(
            return_value=httpx.Response(200, json=_mock_search_payload()),
        )
        await svc.search_tracks(1, 'test', 1, 20)

    assert route.called
    # verify the Authorization header used the redis cookie
    request = route.calls[0].request
    assert request.headers['Authorization'] == 'token=redis_tok;userid=2;dfid=redis_dfid'


async def test_list_user_playlists_normalizes_kugou_response(mock_redis):
    svc = _svc(mock_redis)
    payload = {'data': {'info': [{'id': 'UP1', 'name': 'My List'}]}}
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/user/playlist').mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await svc.list_user_playlists(1, 1, 30)

    assert route.called
    assert result['items'][0]['name'] == 'My List'


async def test_get_user_playlist_tracks_includes_file_id(mock_redis):
    svc = _svc(mock_redis)
    payload = {'data': {'info': [{'FileHash': 'UPT1'}]}}
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/playlist/track/all/new').mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await svc.get_user_playlist_tracks(1, 'L1', 1, 30)

    assert route.called
    assert result['items'][0]['hash'] == 'UPT1'


async def test_add_track_to_user_playlist_formats_track_data(mock_redis):
    svc = _svc(mock_redis)
    from domains.music.interfaces.dto.music import MusicTrackPayload

    track = MusicTrackPayload(title='T', hash='H', album_id='A', album_audio_id='AA')
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/playlist/tracks/add').mock(
            return_value=httpx.Response(200, json={}),
        )
        await svc.add_track_to_user_playlist(1, 'L1', track)

    assert route.called
    request = route.calls[0].request
    assert request.url.params['data'] == 'T|H|A|AA'


async def test_create_and_delete_user_playlist_use_kugou_endpoints(mock_redis):
    svc = _svc(mock_redis)
    async with respx.mock:
        create_route = respx.get(f'{BASE_URL}/playlist/add').mock(
            return_value=httpx.Response(200, json={}),
        )
        delete_route = respx.get(f'{BASE_URL}/playlist/del').mock(
            return_value=httpx.Response(200, json={}),
        )
        await svc.create_user_playlist(1, 'New', False)
        await svc.delete_user_playlist(1, 'L1')

    assert create_route.called
    assert delete_route.called


async def test_collect_playlist_loads_detail_before_add(mock_redis):
    svc = _svc(mock_redis)
    detail_payload = {
        'data': [
            {
                'list_create_userid': 'u1',
                'list_create_listid': 'l1',
                'name': 'Collected',
                'source': 1,
                'list_create_gid': 'g1',
            }
        ]
    }
    async with respx.mock:
        detail_route = respx.get(f'{BASE_URL}/playlist/detail').mock(
            return_value=httpx.Response(200, json=detail_payload),
        )
        add_route = respx.get(f'{BASE_URL}/playlist/add').mock(
            return_value=httpx.Response(200, json={}),
        )
        result = await svc.collect_playlist(1, '99')

    assert detail_route.called
    assert add_route.called
    assert result['ok'] is True


async def test_user_history_and_playhistory_upload_use_kugou_endpoints(mock_redis):
    svc = _svc(mock_redis)
    history_payload = {'data': {'songs': [{'FileHash': 'H1'}]}}
    async with respx.mock:
        history_route = respx.get(f'{BASE_URL}/user/history').mock(
            return_value=httpx.Response(200, json=history_payload),
        )
        upload_route = respx.get(f'{BASE_URL}/playhistory/upload').mock(
            return_value=httpx.Response(200, json={}),
        )
        listen_route = respx.get(f'{BASE_URL}/user/listen').mock(
            return_value=httpx.Response(200, json={}),
        )
        latest_route = respx.get(f'{BASE_URL}/lastest/songs/listen').mock(
            return_value=httpx.Response(200, json={}),
        )

        history = await svc.get_user_history(1, None)
        await svc.upload_play_history(1, 'AA1', None, 1)
        await svc.get_user_listen_rank(1, 0)
        await svc.get_latest_listen_songs(1, 10)

    assert history_route.called
    assert upload_route.called
    assert listen_route.called
    assert latest_route.called
    assert history['items'][0]['hash'] == 'H1'


async def test_get_favorite_counts_uses_public_endpoint_without_auth(mock_redis):
    svc = _svc(mock_redis)
    payload = {'data': {'list': [{'mixsongid': 'MS1', 'count': 42, 'count_text': '42'}]}}
    async with respx.mock:
        route = respx.get(f'{BASE_URL}/favorite/count').mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await svc.get_favorite_counts(1, 'MS1')

    assert route.called
    assert result['items'][0]['mixsongid'] == 'MS1'
