import assert from 'node:assert/strict'
import test from 'node:test'

import {
  __desktopMusicServiceForTests as musicService,
  __setDesktopMusicAuthStoreForTests,
  __setDesktopMusicKugouForTests,
  callDesktopMusic,
} from '../src/music/service.mjs'

const withMockMusicRuntime = async (kugou, fn) => {
  let cookie = ''
  __setDesktopMusicKugouForTests(kugou)
  __setDesktopMusicAuthStoreForTests({
    read: async () => cookie,
    write: async (value) => { cookie = value },
    clear: async () => { cookie = '' },
  })
  try {
    return await fn({
      get cookie() { return cookie },
      setCookie: (value) => { cookie = value },
    })
  } finally {
    __setDesktopMusicKugouForTests(null)
    __setDesktopMusicAuthStoreForTests(null)
  }
}

test('desktop music search normalizes kugou results', async () => {
  await withMockMusicRuntime({
    search: async (params) => {
      assert.equal(params.keywords, 'demo')
      assert.equal(params.type, 'song')
      return {
        body: {
          data: {
            total: 1,
            lists: [{
              AlbumAudioID: 123,
              FileHash: 'ABC',
              SongName: 'Demo Artist - Demo Song',
              SingerName: 'Demo Artist',
              AlbumName: 'Demo Album',
              AlbumID: 456,
              Duration: 210,
              Image: 'https://img.example.test/cover.jpg',
            }],
          },
        },
      }
    },
  }, async () => {
    const result = await musicService.searchTracks({ query: 'demo', page: 1, page_size: 20 })
    assert.deepEqual(result.items, [{
      id: '123',
      title: 'Demo Song',
      artist: 'Demo Artist',
      album: 'Demo Album',
      hash: 'ABC',
      album_id: '456',
      album_audio_id: '123',
      duration: 210,
      cover: 'https://img.example.test/cover.jpg',
    }])
  })
})

test('desktop music play url selects first returned url', async () => {
  await withMockMusicRuntime({
    song_url: async (params) => {
      assert.equal(params.hash, 'HASH')
      assert.equal(params.quality, '320')
      return { body: { url: ['http://cdn.test/a.mp3'], bitRate: '320' } }
    },
  }, async () => {
    assert.deepEqual(
      await musicService.playUrl({ hash: 'HASH', quality: '320' }),
      { url: 'http://cdn.test/a.mp3', quality: '320', expires_at: undefined },
    )
  })
})

test('desktop music play url reads current direct url fields', async () => {
  await withMockMusicRuntime({
    song_url: async () => ({ body: { play_url: 'http://cdn.test/direct.flac', quality: 'flac', expire: 3600 } }),
  }, async () => {
    assert.deepEqual(
      await musicService.playUrl({ hash: 'HASH', quality: 'flac' }),
      { url: 'http://cdn.test/direct.flac', quality: 'flac', expires_at: 3600 },
    )
  })
})

test('desktop music play url surfaces verification errors', async () => {
  await withMockMusicRuntime({
    song_url: async () => ({ body: { status: 0, errcode: 20028, error: '本次请求需要验证' } }),
  }, async () => {
    await assert.rejects(
      musicService.playUrl({ hash: 'HASH' }),
      /需要验证|重新登录/,
    )
  })
})

test('desktop music play url rejects empty playback payloads', async () => {
  await withMockMusicRuntime({
    song_url: async () => ({ body: { url: [], bitRate: '128' } }),
  }, async () => {
    await assert.rejects(
      musicService.playUrl({ hash: 'HASH' }),
      /未返回可播放地址/,
    )
  })
})

test('desktop music qr login stores desktop auth cookie', async () => {
  await withMockMusicRuntime({
    login_qr_check: async () => ({ body: { data: { status: 4, token: 'tok', userid: '99' } } }),
  }, async (runtime) => {
    const result = await musicService.checkQrLogin({ key: 'QR' })
    assert.equal(result.logged_in, true)
    assert.equal(runtime.cookie, 'token=tok;userid=99')
  })
})

test('desktop music qr login accepts token cookies from kugou response', async () => {
  await withMockMusicRuntime({
    login_qr_check: async () => ({
      body: { data: { status: 4 } },
      cookie: ['token=tok;HttpOnly', 'userid=99;HttpOnly'],
    }),
  }, async (runtime) => {
    const result = await musicService.checkQrLogin({ key: 'QR' })
    assert.equal(result.logged_in, true)
    assert.equal(runtime.cookie, 'token=tok;userid=99')
  })
})

test('desktop music qr login preserves dfid when kugou returns it', async () => {
  await withMockMusicRuntime({
    login_qr_check: async () => ({
      body: { data: { status: 4 } },
      cookie: ['token=tok;HttpOnly', 'userid=99;HttpOnly', 'dfid=dfid-1;HttpOnly'],
    }),
  }, async (runtime) => {
    const result = await musicService.checkQrLogin({ key: 'QR' })
    assert.equal(result.logged_in, true)
    assert.equal(runtime.cookie, 'token=tok;userid=99;dfid=dfid-1')
  })
})

test('desktop music rejects unsupported operations', async () => {
  await assert.rejects(
    callDesktopMusic('unsupportedOperation', {}),
    /Unsupported music operation/,
  )
})

test('desktop music normalizer strips artist prefix from track titles', async () => {
  const { normalizeTrack } = await import('../src/music/normalizers.mjs')
  assert.deepEqual(
    normalizeTrack({
      AlbumAudioID: 123,
      FileHash: 'ABC',
      SongName: 'Demo Artist - Demo Song.mp3',
      SingerName: 'Demo Artist',
      AlbumName: 'Demo Album',
      AlbumID: 456,
      Duration: 210,
      Image: 'https://img.example.test/cover.jpg',
    }),
    {
      id: '123',
      title: 'Demo Song',
      artist: 'Demo Artist',
      album: 'Demo Album',
      hash: 'ABC',
      album_id: '456',
      album_audio_id: '123',
      duration: 210,
      cover: 'https://img.example.test/cover.jpg',
    },
  )
})

test('desktop music user playlists returns kugou rows without remapping fields', async () => {
  await withMockMusicRuntime({
    user_playlist: async () => ({
      body: {
        data: {
          total: 1,
          info: [{
            listid: 2,
            name: '我喜欢',
            pic: 'http://c1.kgimg.com/stdmusic/{size}/cover.jpg',
            list_create_listid: 2,
            list_create_userid: 1776217110,
            list_create_gid: 'collection_3_1776217110_2_0',
            type: 0,
            is_def: 2,
            m_count: 99,
          }],
        },
      },
    }),
  }, async () => {
    const result = await musicService.userPlaylists()
    assert.deepEqual(result.items, [{
      listid: 2,
      name: '我喜欢',
      pic: 'http://c1.kgimg.com/stdmusic/{size}/cover.jpg',
      list_create_listid: 2,
      list_create_userid: 1776217110,
      list_create_gid: 'collection_3_1776217110_2_0',
      type: 0,
      is_def: 2,
      m_count: 99,
    }])
  })
})

test('desktop music user profile refreshes token profile fields', async () => {
  await withMockMusicRuntime({
    login_token: async (params) => {
      assert.equal(params.token, 'tok')
      assert.equal(params.userid, '99')
      return {
        body: {
          data: {
            userid: 99,
            nickname: 'Demo User',
            username: 'kgopen99',
            pic: 'http://imge.kugou.com/stdmusic/{size}/avatar.jpg',
            sex: 1,
            reg_time: '2024-01-02',
          },
        },
      }
    },
    user_detail: async (params) => {
      assert.equal(params.cookie, 'token=tok;userid=99')
      assert.equal(params.userid, '99')
      return {
        body: {
          data: {
            p_grade: 7,
            follows: 3,
            fans: 4,
          },
        },
      }
    },
    user_listen: async (params) => {
      assert.equal(params.cookie, 'token=tok;userid=99')
      assert.equal(params.type, 1)
      return {
        body: {
          data: {
            total_history: 730,
          },
        },
      }
    },
  }, async (runtime) => {
    runtime.setCookie('token=tok;userid=99')
    const result = await musicService.userProfile()
    assert.deepEqual(result, {
      userid: '99',
      nickname: 'Demo User',
      avatar: 'http://imge.kugou.com/stdmusic/240/avatar.jpg',
      level: 7,
      gender: '1',
      register_time: '2024-01-02',
      follow_count: 3,
      fan_count: 4,
      listen_count: 730,
    })
  })
})

test('desktop music user history maps nested kugou song info', async () => {
  await withMockMusicRuntime({
    user_history: async () => ({
      body: {
        data: {
          bp: 'next-bp',
          songs: [{
            mxid: 733384462,
            info: {
              name: '推开世界的门',
              singername: '赵乃吉',
              hash: 'D659C5B602EBB9F4D28E59D9F9A58403',
              timelen: 214334,
              cover: 'http://imge.kugou.com/stdmusic/{size}/cover.jpg',
              mixsongid: 733384462,
              album_id: 141541684,
              albuminfo: { name: '推开世界的门', id: 141541684 },
              singerinfo: [{ name: '赵乃吉', id: 173618 }],
            },
          }],
        },
      },
    }),
  }, async () => {
    const result = await musicService.userHistory()
    assert.deepEqual(result, {
      items: [{
        id: '733384462',
        title: '推开世界的门',
        artist: '赵乃吉',
        album: '推开世界的门',
        hash: 'D659C5B602EBB9F4D28E59D9F9A58403',
        album_id: '141541684',
        album_audio_id: '733384462',
        duration: 214,
        cover: 'http://imge.kugou.com/stdmusic/240/cover.jpg',
        artist_id: '173618',
      }],
      bp: 'next-bp',
    })
  })
})

test('desktop music user listen rank reads kugou lists field', async () => {
  await withMockMusicRuntime({
    user_listen: async (params) => {
      assert.equal(params.type, 1)
      return {
        body: {
          data: {
            lists: [{
              id: 192661823,
              name: '王菲 - 归途有风',
              singername: '王菲',
              album_name: '归途有风',
              hash: '6B35FA7A119D35FF11C244F0BBE88019',
              album_audio_id: 445459508,
              duration: 320000,
              image: 'http://imge.kugou.com/stdmusic/{size}/cover.jpg',
            }],
          },
        },
      }
    },
  }, async () => {
    const result = await musicService.userListenRank({ type: 1 })
    assert.deepEqual(result.items, [{
      id: '445459508',
      title: '归途有风',
      artist: '王菲',
      album: '归途有风',
      hash: '6B35FA7A119D35FF11C244F0BBE88019',
      album_id: '',
      album_audio_id: '445459508',
      duration: 320,
      cover: 'http://imge.kugou.com/stdmusic/240/cover.jpg',
    }])
  })
})
