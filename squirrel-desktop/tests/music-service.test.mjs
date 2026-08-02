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
      /酷狗播放接口需要验证，请重新登录音乐账号后再播放/,
    )
  })
})

test('desktop music play url revalidates session once after captcha error', async () => {
  let songUrlCalls = 0
  let loginTokenCalls = 0
  await withMockMusicRuntime({
    song_url: async () => {
      songUrlCalls += 1
      if (songUrlCalls === 1) {
        return { body: { status: 0, errcode: 20028, error: '本次请求需要验证' } }
      }
      return { body: { url: 'http://cdn.test/recovered.mp3', bitRate: '128' } }
    },
    login_token: async () => {
      loginTokenCalls += 1
      return { body: { status: 1, data: { userid: '1', token: 'tok' } } }
    },
  }, async (runtime) => {
    runtime.setCookie('token=tok;userid=1')
    assert.deepEqual(
      await musicService.playUrl({ hash: 'HASH' }),
      { url: 'http://cdn.test/recovered.mp3', quality: '128', expires_at: undefined },
    )
    assert.equal(songUrlCalls, 2)
    assert.equal(loginTokenCalls, 1)
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


test('desktop music lyric reads nested candidates and decoded content', async () => {
  await withMockMusicRuntime({
    search_lyric: async (params) => {
      assert.equal(params.keyword, undefined)
      assert.equal(params.keywords, 'Demo Artist - Demo Song')
      assert.equal(params.hash, 'HASH')
      return {
        body: {
          data: {
            candidates: [{ id: 'lyric-1', accesskey: 'access-1' }],
          },
        },
      }
    },
    lyric: async (params) => {
      assert.equal(params.id, 'lyric-1')
      assert.equal(params.accesskey, 'access-1')
      assert.equal(params.fmt, 'lrc')
      return { body: { data: { decodeContent: '[00:01.00]第一句\\n[00:02.50]第二句' } } }
    },
  }, async () => {
    assert.deepEqual(
      await musicService.lyric({ title: 'Demo Song', artist: 'Demo Artist', hash: 'HASH' }),
      { lines: [{ time: 1, text: '第一句' }, { time: 2.5, text: '第二句' }] },
    )
  })
})

test('desktop music lyric falls back to base64 content', async () => {
  await withMockMusicRuntime({
    search_lyric: async () => ({ body: { candidates: [{ id: 'lyric-1', accessKey: 'access-1' }] } }),
    lyric: async () => ({ body: { content: Buffer.from('[00:03.00]第三句', 'utf8').toString('base64') } }),
  }, async () => {
    assert.deepEqual(
      await musicService.lyric({ title: 'Demo Song', hash: 'HASH' }),
      { lines: [{ time: 3, text: '第三句' }] },
    )
  })
})


test('desktop music lyric accepts kugou OK status payloads', async () => {
  await withMockMusicRuntime({
    search_lyric: async () => ({ body: { status: 200, message: 'OK', candidates: [{ id: 'lyric-1', accesskey: 'access-1' }] } }),
    lyric: async () => ({ body: { status: 200, message: 'OK', decodeContent: '[00:04.00]OK 状态下的歌词' } }),
  }, async () => {
    assert.deepEqual(
      await musicService.lyric({ title: 'Demo Song', hash: 'HASH' }),
      { lines: [{ time: 4, text: 'OK 状态下的歌词' }] },
    )
  })
})


test('desktop music lyric skips placeholder candidates', async () => {
  const requestedIds = []
  await withMockMusicRuntime({
    search_lyric: async () => ({
      body: {
        candidates: [
          { id: 'placeholder', accesskey: 'access-1' },
          { id: 'real', accesskey: 'access-2' },
        ],
      },
    }),
    lyric: async (params) => {
      requestedIds.push(params.id)
      if (params.id === 'placeholder') return { body: { decodeContent: '[00:00.00]OK' } }
      return { body: { decodeContent: '[00:04.00]真正歌词' } }
    },
  }, async () => {
    assert.deepEqual(
      await musicService.lyric({ title: 'Demo Song', hash: 'HASH' }),
      { lines: [{ time: 4, text: '真正歌词' }] },
    )
    assert.deepEqual(requestedIds, ['placeholder', 'real'])
  })
})


test('desktop music lyric retries clean title search after placeholder results', async () => {
  const searchParams = []
  await withMockMusicRuntime({
    search_lyric: async (params) => {
      searchParams.push(params)
      if (params.hash || params.album_audio_id) {
        return { body: { candidates: [{ id: 'placeholder', accesskey: 'access-1' }] } }
      }
      return { body: { candidates: [{ id: 'real', accesskey: 'access-2' }] } }
    },
    lyric: async (params) => {
      if (params.id === 'placeholder') return { body: { decodeContent: '[00:00.00]OK' } }
      return { body: { decodeContent: "[00:07.55]No I can't forget this evening" } }
    },
  }, async () => {
    assert.deepEqual(
      await musicService.lyric({ title: 'Without You', artist: 'Vanny Vabiola', hash: 'BADHASH', album_audio_id: '123', duration: 244 }),
      { lines: [{ time: 7.55, text: "No I can't forget this evening" }] },
    )
    assert.equal(searchParams.length, 2)
    assert.equal(searchParams[0].hash, 'BADHASH')
    assert.equal(searchParams[1].hash, '')
    assert.equal(searchParams[1].keywords, 'Vanny Vabiola - Without You')
  })
})

test('desktop music qr login stores desktop auth cookie', async () => {
  await withMockMusicRuntime({
    login_token: async () => ({ body: { status: 1, data: { userid: '99', token: 'tok' } } }),
    login_qr_check: async () => ({ body: { data: { status: 4, token: 'tok', userid: '99' } } }),
  }, async (runtime) => {
    const result = await musicService.checkQrLogin({ key: 'QR' })
    assert.equal(result.logged_in, true)
    assert.equal(runtime.cookie, 'token=tok;userid=99')
  })
})

test('desktop music qr login accepts token cookies from kugou response', async () => {
  await withMockMusicRuntime({
    login_token: async () => ({ body: { status: 1, data: { userid: '99', token: 'tok' } } }),
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
    login_token: async () => ({ body: { status: 1, data: { userid: '99', token: 'tok' } } }),
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


test('desktop music vip claim status combines reward and vip data', async () => {
  await withMockMusicRuntime({
    youth_union_vip: async () => ({ body: { data: { is_receive: 1, receive_day: '2026-08-02' } } }),
    youth_month_vip_record: async () => ({ body: { data: { count: 3 } } }),
    user_vip_detail: async () => ({ body: { data: { is_vip: 1, vip_type: 2, vip_expire_time: '2026-08-03', vip_level: 1 } } }),
  }, async () => {
    assert.deepEqual(await musicService.vipClaimStatus(), {
      is_vip: true,
      vip_type: 2,
      vip_expire_time: '2026-08-03',
      vip_level: 1,
      received_today: true,
      receive_day: '2026-08-02',
      month_received_days: 3,
      raw_status: { is_receive: 1, receive_day: '2026-08-02' },
    })
  })
})

test('desktop music daily vip claim uses today by default and returns refreshed status', async () => {
  let receivedDay = ''
  await withMockMusicRuntime({
    login_token: async () => ({ body: { status: 1, data: { userid: '99', token: 'tok' } } }),
    youth_day_vip: async (params) => {
      receivedDay = params.receive_day
      assert.match(receivedDay, /^\d{4}-\d{2}-\d{2}$/)
      return { body: { msg: 'ok' } }
    },
    youth_day_vip_upgrade: async () => ({ body: { msg: 'upgraded' } }),
    youth_union_vip: async () => ({ body: { data: { is_receive: 1 } } }),
    youth_month_vip_record: async () => ({ body: { data: { receive_days: 4 } } }),
    user_vip_detail: async () => ({ body: { data: { vip_type: 1 } } }),
  }, async (runtime) => {
    runtime.setCookie('token=tok;userid=99')
    const result = await musicService.claimDailyVip({})
    assert.equal(result.receive_day, receivedDay)
    assert.equal(result.received_today, true)
    assert.equal(result.month_received_days, 4)
    assert.equal(result.is_vip, true)
    assert.equal(result.message, 'ok')
  })
})




test('desktop music daily vip claim does not mark received without verified VIP grant', async () => {
  await withMockMusicRuntime({
    login_token: async () => ({ body: { status: 1, data: { userid: '99', token: 'tok' } } }),
    youth_day_vip: async () => Promise.reject({ body: { status: 0, error_code: 51002 } }),
    youth_vip: async () => ({ body: { status: 1, data: {} } }),
    youth_day_vip_upgrade: async () => ({ body: { status: 1, data: {} } }),
    youth_union_vip: async () => ({ body: { data: { is_vip: 0 } } }),
    youth_month_vip_record: async () => ({ body: { data: { receive_days: 0 } } }),
    user_vip_detail: async () => ({ body: { data: { vip_type: 0 } } }),
  }, async (runtime) => {
    runtime.setCookie('token=tok;userid=99')
    const result = await musicService.claimDailyVip({ receive_day: '2026-08-02' })
    assert.equal(result.received_today, false)
    assert.match(result.message, /未返回 VIP 发放结果/)
  })
})

test('desktop music auth status logs out expired kugou auth centrally', async () => {
  await withMockMusicRuntime({
    login_token: async () => Promise.reject({ body: { status: 0, error_code: 131001, error_msg: '' } }),
  }, async (runtime) => {
    runtime.setCookie('token=stale;userid=99')
    assert.deepEqual(await musicService.authStatus(), { logged_in: false, source: '', userid: '' })
    assert.equal(runtime.cookie, '')
  })
})

test('desktop music daily vip claim surfaces kugou rejection messages', async () => {
  await withMockMusicRuntime({
    login_token: async () => ({ body: { status: 1, data: { userid: '99', token: 'tok' } } }),
    youth_day_vip: async () => Promise.reject({
      body: {
        status: 0,
        msg: {
          response: {
            data: { status: 0, error: '活动暂未开放' },
          },
        },
      },
    }),
  }, async (runtime) => {
    runtime.setCookie('token=tok;userid=99')
    await assert.rejects(
      musicService.claimDailyVip({ receive_day: '2026-08-02' }),
      /活动暂未开放/,
    )
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

test('desktop theme playlists use the matching theme track endpoint', async () => {
  await withMockMusicRuntime({
    theme_playlist_track: async (params) => {
      assert.equal(params.theme_id, '39')
      return {
        body: {
          data: {
            song_list_size: 1,
            song_list: [{
              songid: 517186507,
              songname: '珠玉',
              author_name: '单依纯',
              album_name: '珠玉',
              hash: 'C1B40CC00A2B9C31450F89275ED28DC6',
              album_id: '146854336',
              album_audio_id: '753057489',
              timelength: 202,
              sizable_cover: 'http://imge.kugou.com/stdmusic/{size}/cover.jpg',
            }],
          },
        },
      }
    },
    playlist_track_all: async () => {
      assert.fail('theme playlists must not use the ordinary playlist endpoint')
    },
  }, async () => {
    const result = await musicService.playlistTracks({
      playlist_id: '39',
      playlist_kind: 'theme',
      page: 1,
      page_size: 30,
    })

    assert.equal(result.total, 1)
    assert.deepEqual(result.items, [{
      id: '753057489',
      title: '珠玉',
      artist: '单依纯',
      album: '珠玉',
      hash: 'C1B40CC00A2B9C31450F89275ED28DC6',
      album_id: '146854336',
      album_audio_id: '753057489',
      duration: 202,
      cover: 'http://imge.kugou.com/stdmusic/240/cover.jpg',
    }])
  })
})
