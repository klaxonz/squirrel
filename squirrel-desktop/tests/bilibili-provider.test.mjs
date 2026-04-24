import assert from 'node:assert/strict'
import test from 'node:test'

import { resolveBilibiliPlayback } from '../src/playback/providers/bilibili/index.mjs'
import { resolveBilibiliApiPayload } from '../src/playback/providers/bilibili/request-runtime.mjs'

test('desktop bilibili provider builds codec-separated video adaptation sets with unique representation ids', async () => {
  const originalFetch = globalThis.fetch
  const responseMap = new Map([
    [
      'https://api.bilibili.com/x/web-interface/nav',
      {
        code: 0,
        data: {
          wbi_img: {
            img_url: 'https://i0.hdslb.com/bfs/wbi/abcdefghijklmnopqrstuvwxyz123456.png',
            sub_url: 'https://i0.hdslb.com/bfs/wbi/123456abcdefghijklmnopqrstuvwxyz7890.png',
          },
        },
      },
    ],
    [
      'https://api.bilibili.com/x/web-interface/view',
      {
        code: 0,
        data: {
          bvid: 'BV1BfobBREWE',
          aid: 116451478472399,
          pages: [{ cid: 37738447455 }],
        },
      },
    ],
  ])

  globalThis.fetch = async (input) => {
    const url = new URL(String(input))
    if (url.origin === 'https://api.bilibili.com' && url.pathname === '/x/player/wbi/playurl') {
      return {
        ok: true,
        status: 200,
        async json() {
          return {
            code: 0,
            data: {
              dash: {
                duration: 120,
                minBufferTime: 1.5,
                video: [
                  {
                    id: 80,
                    codecid: 7,
                    codecs: 'avc1.640033',
                    width: 1920,
                    height: 1080,
                    bandwidth: 456306,
                    baseUrl: 'https://cdn.example.test/avc-1080.m4s',
                    SegmentBase: {
                      indexRange: '945-4768',
                      Initialization: '0-944',
                    },
                  },
                  {
                    id: 80,
                    codecid: 13,
                    codecs: 'av01.0.00M.10.0.110.01.01.01.0',
                    width: 1920,
                    height: 1080,
                    bandwidth: 339781,
                    baseUrl: 'https://cdn.example.test/av1-1080.m4s',
                    SegmentBase: {
                      indexRange: '945-4768',
                      Initialization: '0-944',
                    },
                  },
                  {
                    id: 64,
                    codecid: 7,
                    codecs: 'avc1.64001f',
                    width: 1280,
                    height: 720,
                    bandwidth: 250139,
                    baseUrl: 'https://cdn.example.test/avc-720.m4s',
                    SegmentBase: {
                      indexRange: '945-4768',
                      Initialization: '0-944',
                    },
                  },
                  {
                    id: 64,
                    codecid: 13,
                    codecs: 'av01.0.00M.10.0.110.01.01.01.0',
                    width: 1280,
                    height: 720,
                    bandwidth: 196961,
                    baseUrl: 'https://cdn.example.test/av1-720.m4s',
                    SegmentBase: {
                      indexRange: '945-4768',
                      Initialization: '0-944',
                    },
                  },
                ],
                audio: [
                  {
                    id: 30280,
                    codecs: 'mp4a.40.2',
                    bandwidth: 84522,
                    baseUrl: 'https://cdn.example.test/audio.m4s',
                    SegmentBase: {
                      indexRange: '945-4768',
                      Initialization: '0-944',
                    },
                  },
                ],
              },
            },
          }
        },
      }
    }

    const key = `${url.origin}${url.pathname}`
    const payload = responseMap.get(key)
    if (!payload) {
      throw new Error(`Unexpected fetch: ${url.toString()}`)
    }

    return {
      ok: true,
      status: 200,
      async json() {
        return payload
      },
    }
  }

  try {
    const payload = await resolveBilibiliPlayback('https://www.bilibili.com/video/BV1BfobBREWE', {
      cookie: '',
      forceRefresh: true,
    })

    assert.equal(payload.stream_type, 'dash')
    assert.equal(Boolean(payload.mpd_content), true)
    assert.deepEqual(
      payload.qualities?.map((item) => item.id),
      [
        'video-avc-80-1080-456306',
        'video-av1-80-1080-339781',
        'video-avc-64-720-250139',
        'video-av1-64-720-196961',
      ],
    )

    const representationIds = [...payload.mpd_content.matchAll(/<Representation [^>]*id="([^"]+)"/g)].map((match) => match[1])
    const videoAdaptationSets = [...payload.mpd_content.matchAll(/<AdaptationSet contentType="video"[\s\S]*?<\/AdaptationSet>/g)]
    assert.equal(representationIds.length, 5)
    assert.equal(new Set(representationIds).size, representationIds.length)
    assert.equal(videoAdaptationSets.length, 2)
    assert.match(videoAdaptationSets[0][0] + videoAdaptationSets[1][0], /codecs="avc1\.640033"/)
    assert.match(videoAdaptationSets[0][0] + videoAdaptationSets[1][0], /codecs="av01\.0\.00M\.10\.0\.110\.01\.01\.01\.0"/)
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('desktop bilibili request runtime accepts injected fetch implementations', async () => {
  const calls = []
  const fetchImpl = async (input) => {
    const url = new URL(String(input))
    calls.push(url.toString())

    if (url.pathname === '/x/web-interface/view') {
      return {
        ok: true,
        status: 200,
        async text() {
          return JSON.stringify({
            code: 0,
            data: {
              bvid: 'BV1LooLBUEf9',
              aid: 116460101831801,
              pages: [{ cid: 37789109465 }],
            },
          })
        },
      }
    }

    if (url.pathname === '/x/web-interface/nav') {
      return {
        ok: true,
        status: 200,
        async text() {
          return JSON.stringify({
            code: 0,
            data: {
              isLogin: true,
              wbi_img: {
                img_url: 'https://i0.hdslb.com/bfs/wbi/abcdefghijklmnopqrstuvwxyz123456.png',
                sub_url: 'https://i0.hdslb.com/bfs/wbi/123456abcdefghijklmnopqrstuvwxyz7890.png',
              },
            },
          })
        },
      }
    }

    if (url.pathname === '/x/player/wbi/playurl') {
      return {
        ok: true,
        status: 200,
        async text() {
          return JSON.stringify({
            code: 0,
            data: {
              quality: 80,
              dash: {
                duration: 76,
                minBufferTime: 1.5,
                video: [
                  {
                    id: 80,
                    codecid: 7,
                    codecs: 'avc1.640033',
                    width: 1920,
                    height: 1080,
                    bandwidth: 456306,
                    baseUrl: 'https://cdn.example.test/avc-1080.m4s',
                    SegmentBase: {
                      indexRange: '945-4768',
                      Initialization: '0-944',
                    },
                  },
                ],
                audio: [
                  {
                    id: 30280,
                    codecs: 'mp4a.40.2',
                    bandwidth: 84522,
                    baseUrl: 'https://cdn.example.test/audio.m4s',
                    SegmentBase: {
                      indexRange: '945-4768',
                      Initialization: '0-944',
                    },
                  },
                ],
              },
            },
          })
        },
      }
    }

    throw new Error(`Unexpected injected fetch: ${url.toString()}`)
  }

  const payload = await resolveBilibiliApiPayload('https://www.bilibili.com/video/BV1LooLBUEf9', {
    cookie: 'SESSDATA=demo',
    fetchImpl,
  })

  assert.equal(payload.context.cid, 37789109465)
  assert.equal(payload.playData?.quality, 80)
  assert.equal(calls.length, 3)
  assert.match(calls[0], /\/x\/web-interface\/view/)
  assert.match(calls[1], /\/x\/web-interface\/nav/)
  assert.match(calls[2], /\/x\/player\/wbi\/playurl/)
})
