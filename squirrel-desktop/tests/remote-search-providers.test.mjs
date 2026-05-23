import assert from 'node:assert/strict'
import test from 'node:test'

import { getRemoteChannel } from '../src/search/providers/remote-channel.mjs'
import { searchBilibiliVideos } from '../src/search/providers/bilibili.mjs'
import { searchRemoteVideos } from '../src/search/providers/index.mjs'
import { searchJavdbVideos } from '../src/search/providers/javdb.mjs'
import { searchPornhubVideos } from '../src/search/providers/pornhub.mjs'
import { searchYouPornVideos } from '../src/search/providers/youporn.mjs'
import { searchYouTubeVideos } from '../src/search/providers/youtube.mjs'

const jsonResponse = (payload) => new Response(JSON.stringify(payload), {
  status: 200,
  headers: { 'content-type': 'application/json' },
})

const htmlResponse = (html) => new Response(html, {
  status: 200,
  headers: { 'content-type': 'text/html' },
})

const buildCookieHeader = async () => 'SESSDATA=test'
const loadJavdbDocumentHtml = async () => `
  <div class="item">
    <a href="/v/demo">
      <img src="https://javdb.com/demo.jpg">
      <div class="video-title"><strong>DEMO-001</strong> Demo JAVDB</div>
      <div class="score"><span class="value">7.5</span></div>
      <div class="meta">2026-01-02</div>
      <a href="/actors/demo-actor">Demo Actor</a>
    </a>
  </div>
`

test('desktop bilibili remote search maps api results', async () => {
  let requestedUrl = ''
  const items = await searchBilibiliVideos({
    query: 'demo',
    limit: 5,
    page: 2,
    buildCookieHeader,
    fetchImpl: async (url) => {
      if (url.includes('/x/web-interface/card')) {
        return jsonResponse({
          data: {
            card: {
              mid: '12345',
              name: 'Uploader',
              face: '//i0.hdslb.com/avatar.jpg',
            },
          },
        })
      }

      requestedUrl = url
      return jsonResponse({
        data: {
          result: [
            {
              bvid: 'BV1demo',
              title: '<em class="keyword">Demo</em> Video',
              arcurl: 'https://www.bilibili.com/video/BV1demo',
              pic: '//i0.hdslb.com/demo.jpg',
              duration: '01:02',
              pubdate: 1700000000,
              author: 'Uploader',
              mid: 12345,
              upic: '',
            },
          ],
        },
      })
    },
  })

  assert.equal(items.length, 1)
  assert.equal(items[0].site, 'bilibili')
  assert.equal(items[0].title, 'Demo Video')
  assert.equal(items[0].duration, 62)
  assert.equal(items[0].uploader_url, 'https://space.bilibili.com/12345')
  assert.equal(items[0].uploader_avatar, 'https://i0.hdslb.com/avatar.jpg')
  assert.deepEqual(items[0].subscriptions, [{
    id: 12345,
    type: 'CHANNEL',
    name: 'Uploader',
    url: 'https://space.bilibili.com/12345',
    avatar: 'https://i0.hdslb.com/avatar.jpg',
    is_nsfw: false,
  }])
  assert.equal(new URL(requestedUrl).searchParams.get('page'), '2')
})

test('desktop youtube remote search extracts video renderers', async () => {
  const initialData = {
    contents: {
      sectionListRenderer: {
        contents: [
          {
            itemSectionRenderer: {
              contents: [
                {
                  videoRenderer: {
                    videoId: 'abc123',
                    title: { runs: [{ text: 'Demo YouTube Video' }] },
                    thumbnail: { thumbnails: [{ url: 'https://i.ytimg.com/vi/abc123/hqdefault.jpg' }] },
                    lengthText: { simpleText: '1:03' },
                    ownerText: {
                      runs: [{
                        text: 'Demo Channel',
                        navigationEndpoint: {
                          browseEndpoint: { browseId: 'UCdemo', canonicalBaseUrl: '/@demo' },
                          commandMetadata: { webCommandMetadata: { url: '/@demo' } },
                        },
                      }],
                    },
                    channelThumbnailSupportedRenderers: {
                      channelThumbnailWithLinkRenderer: {
                        thumbnail: {
                          thumbnails: [{ url: 'https://yt3.ggpht.com/demo-avatar=s88-c-k-c0x00ffffff-no-rj' }],
                        },
                      },
                    },
                    publishedTimeText: { simpleText: '2 days ago' },
                  },
                },
              ],
            },
          },
        ],
      },
    },
  }

  const result = await searchYouTubeVideos({
    query: 'demo',
    limit: 5,
    buildCookieHeader,
    fetchImpl: async () => htmlResponse(`
      <script>ytcfg.set({"INNERTUBE_API_KEY":"test-key","INNERTUBE_CONTEXT":{"client":{"clientName":"WEB","clientVersion":"1.0"}}});</script>
      <script>var ytInitialData = ${JSON.stringify(initialData)};</script>
    `),
  })

  const items = result.items
  assert.equal(items.length, 1)
  assert.equal(items[0].site, 'youtube')
  assert.equal(items[0].url, 'https://www.youtube.com/watch?v=abc123')
  assert.equal(items[0].duration, 63)
  assert.equal(items[0].uploader_url, 'https://www.youtube.com/@demo')
  assert.equal(items[0].uploader_avatar, 'https://yt3.ggpht.com/demo-avatar=s88-c-k-c0x00ffffff-no-rj')
  assert.deepEqual(items[0].subscriptions, [{
    id: 'UCdemo',
    type: 'CHANNEL',
    name: 'Demo Channel',
    url: 'https://www.youtube.com/@demo',
    avatar: 'https://yt3.ggpht.com/demo-avatar=s88-c-k-c0x00ffffff-no-rj',
    is_nsfw: false,
  }])
  assert.equal(result.has_more, false)
})

test('desktop youtube remote search extracts lockup view models', async () => {
  const initialData = {
    contents: {
      twoColumnSearchResultsRenderer: {
        primaryContents: {
          sectionListRenderer: {
            contents: [
              {
                itemSectionRenderer: {
                  contents: [
                    {
                      lockupViewModel: {
                        contentImage: {
                          thumbnailViewModel: {
                            image: {
                              sources: [{ url: 'https://i.ytimg.com/vi/lock123/hqdefault.jpg' }],
                            },
                            overlays: [
                              {
                                thumbnailBottomOverlayViewModel: {
                                  badges: [
                                    { thumbnailBadgeViewModel: { text: '05:41' } },
                                  ],
                                },
                              },
                            ],
                          },
                        },
                        metadata: {
                          lockupMetadataViewModel: {
                            title: { content: 'Lockup YouTube Video' },
                            metadata: {
                              contentMetadataViewModel: {
                                metadataRows: [
                                  {
                                    metadataParts: [
                                      {
                                        text: {
                                          content: 'Demo Channel',
                                          commandRuns: [
                                            {
                                              text: 'Demo Channel',
                                              onTap: {
                                                innertubeCommand: {
                                                  browseEndpoint: { browseId: 'UCdemo', canonicalBaseUrl: '/@demo' },
                                                  commandMetadata: { webCommandMetadata: { url: '/@demo' } },
                                                },
                                              },
                                            },
                                          ],
                                        },
                                      },
                                      { text: { content: '3 days ago' } },
                                    ],
                                  },
                                ],
                              },
                            },
                          },
                        },
                        rendererContext: {
                          commandContext: {
                            onTap: {
                              innertubeCommand: {
                                watchEndpoint: { videoId: 'lock123' },
                              },
                            },
                          },
                        },
                      },
                    },
                  ],
                },
              },
            ],
          },
        },
      },
    },
  }

  const result = await searchYouTubeVideos({
    query: 'demo',
    limit: 5,
    buildCookieHeader,
    fetchImpl: async () => htmlResponse(`
      <script>ytcfg.set({"INNERTUBE_API_KEY":"test-key","INNERTUBE_CONTEXT":{"client":{"clientName":"WEB","clientVersion":"1.0"}}});</script>
      <script>var ytInitialData = ${JSON.stringify(initialData)};</script>
    `),
  })

  assert.equal(result.items.length, 1)
  assert.equal(result.items[0].title, 'Lockup YouTube Video')
  assert.equal(result.items[0].url, 'https://www.youtube.com/watch?v=lock123')
  assert.equal(result.items[0].duration, 341)
  assert.equal(result.items[0].published_text, '3 days ago')
  assert.equal(result.items[0].uploader_url, 'https://www.youtube.com/@demo')
})

test('desktop youtube remote search loads continuation pages', async () => {
  const requests = []
  const initialData = {
    contents: {
      twoColumnSearchResultsRenderer: {
        primaryContents: {
          sectionListRenderer: {
            contents: [
              {
                itemSectionRenderer: {
                  contents: [
                    {
                      videoRenderer: {
                        videoId: 'abc123',
                        title: { runs: [{ text: 'First Page Video' }] },
                      },
                    },
                  ],
                },
              },
              {
                continuationItemRenderer: {
                  continuationEndpoint: {
                    continuationCommand: { token: 'CONTINUATION_1' },
                  },
                },
              },
            ],
          },
        },
      },
    },
  }
  const continuationData = {
    onResponseReceivedCommands: [
      {
        appendContinuationItemsAction: {
          continuationItems: [
            {
              itemSectionRenderer: {
                contents: [
                  {
                    videoRenderer: {
                      videoId: 'def456',
                      title: { runs: [{ text: 'Second Page Video' }] },
                      lengthText: { simpleText: '02:34' },
                    },
                  },
                ],
              },
            },
            {
              continuationItemRenderer: {
                continuationEndpoint: {
                  continuationCommand: { token: 'CONTINUATION_2' },
                },
              },
            },
          ],
        },
      },
    ],
  }

  const result = await searchYouTubeVideos({
    query: 'demo',
    limit: 1,
    page: 2,
    buildCookieHeader,
    fetchImpl: async (url, options = {}) => {
      requests.push({ url, options })
      if (String(url).includes('/youtubei/v1/search')) return jsonResponse(continuationData)
      return htmlResponse(`
        <script>ytcfg.set({"INNERTUBE_API_KEY":"test-key","INNERTUBE_CONTEXT":{"client":{"clientName":"WEB","clientVersion":"1.0"}}});</script>
        <script>var ytInitialData = ${JSON.stringify(initialData)};</script>
      `)
    },
  })

  assert.equal(requests[1].url, 'https://www.youtube.com/youtubei/v1/search?key=test-key')
  assert.equal(requests[1].options.method, 'POST')
  assert.equal(JSON.parse(requests[1].options.body).continuation, 'CONTINUATION_1')
  assert.equal(result.items.length, 1)
  assert.equal(result.items[0].url, 'https://www.youtube.com/watch?v=def456')
  assert.equal(result.items[0].duration, 154)
  assert.equal(result.has_more, true)
})

test('desktop pornhub remote search parses video list items', async () => {
  const items = await searchPornhubVideos({
    query: 'demo',
    limit: 5,
    buildCookieHeader,
    fetchImpl: async () => htmlResponse(`
      <li class="pcVideoListItem videoblock" data-video-vkey="ph-demo">
        <a href="/view_video.php?viewkey=ph-demo" title="Demo PH" data-title="Demo PH">
          <img data-mediumthumb="https://ei.phncdn.com/demo.jpg">
        </a>
        <div class="usernameWrap"><a href="/users/demo-channel">Demo Channel</a></div>
        <a href="/pornstar/demo-actor">Demo Actor</a>
        <var class="duration">04:05</var>
      </li>
    `),
  })

  assert.equal(items.length, 1)
  assert.equal(items[0].site, 'pornhub')
  assert.equal(items[0].title, 'Demo PH')
  assert.equal(items[0].duration, 245)
  assert.deepEqual(items[0].subscriptions, [{
    type: 'CHANNEL',
    name: 'Demo Channel',
    url: 'https://www.pornhub.com/users/demo-channel',
    avatar: '',
    is_nsfw: true,
  }])
  assert.deepEqual(items[0].actors, [{
    type: 'ACTOR',
    name: 'Demo Actor',
    url: 'https://www.pornhub.com/pornstar/demo-actor',
    avatar: '',
  }])
})

test('desktop youporn remote search parses watch links', async () => {
  const items = await searchYouPornVideos({
    query: 'demo',
    limit: 5,
    buildCookieHeader,
    fetchImpl: async () => htmlResponse(`
      <article class="video-box pc js_video-box" aria-label="Demo YP">
        <a href="/watch/123/demo/" data-testid="plw_video_thumbnail_link">
          <img
            data-src="https://fi.ypncdn.com/demo.jpg"
            src="data:image/png;base64,placeholder"
            alt="Demo YP"
            data-mediabook="https://ev.ypncdn.com/demo.mp4?hash=abc&amp;validto=123"
          >
        </a>
        <span class="duration">05:06</span>
        <a href="/watch/123/demo/" class="video-title-text"><span>Demo YP</span></a>
        <a href="/channels/demo-channel/">Demo Channel</a>
        <a href="/pornstar/demo-actor/">Demo Actor</a>
      </article>
    `),
  })

  assert.equal(items.length, 1)
  assert.equal(items[0].site, 'youporn')
  assert.equal(items[0].url, 'https://www.youporn.com/watch/123/demo/')
  assert.equal(items[0].thumbnail, 'https://fi.ypncdn.com/demo.jpg')
  assert.equal(items[0].duration, 306)
  assert.deepEqual(items[0].subscriptions, [{
    type: 'CHANNEL',
    name: 'Demo Channel',
    url: 'https://www.youporn.com/channels/demo-channel/',
    avatar: '',
    is_nsfw: true,
  }])
  assert.deepEqual(items[0].actors, [{
    type: 'ACTOR',
    name: 'Demo Actor',
    url: 'https://www.youporn.com/pornstar/demo-actor/',
    avatar: '',
  }])
})

test('desktop youporn remote search keeps dynamic cdn thumbnails', async () => {
  const items = await searchYouPornVideos({
    query: 'demo',
    limit: 5,
    buildCookieHeader,
    fetchImpl: async () => htmlResponse(`
      <article class="video-box pc js_video-box" aria-label="Dynamic YP">
        <a href="/watch/456/dynamic/" data-testid="plw_video_thumbnail_link">
          <img
            data-src="https://pix-cdn77.ypncdn.com/c6251/videos/202601/26/37456675/240P_1000K_37456675.mp4/plain/rs:fit:320:180/vts:167?hash=abc&amp;validto=123"
            src="data:image/png;base64,placeholder"
            alt="Dynamic YP"
          >
        </a>
        <span class="duration">03:43</span>
        <a href="/watch/456/dynamic/" class="video-title-text"><span>Dynamic YP</span></a>
      </article>
    `),
  })

  assert.equal(items.length, 1)
  assert.equal(
    items[0].thumbnail,
    'https://pix-cdn77.ypncdn.com/c6251/videos/202601/26/37456675/240P_1000K_37456675.mp4/plain/rs:fit:320:180/vts:167?hash=abc&validto=123'
  )
})

test('desktop javdb remote search parses movie items', async () => {
  const items = await searchJavdbVideos({
    query: 'demo',
    limit: 5,
    loadDocumentHtml: loadJavdbDocumentHtml,
  })

  assert.equal(items.length, 1)
  assert.equal(items[0].site, 'javdb')
  assert.equal(items[0].title, 'DEMO-001 Demo JAVDB')
  assert.equal(items[0].url, 'https://javdb.com/v/demo')
  assert.equal(items[0].publish_date, '2026-01-02')
  assert.deepEqual(items[0].actors, [{
    type: 'ACTOR',
    name: 'Demo Actor',
    url: 'https://javdb.com/actors/demo-actor',
    avatar: '',
  }])
})

test('desktop remote search response carries pagination metadata', async () => {
  const result = await searchRemoteVideos({
    query: 'demo',
    site: 'bilibili',
    limit: 1,
    page: 3,
    buildCookieHeader,
    loadDocumentHtml: loadJavdbDocumentHtml,
    fetchImpl: async () => jsonResponse({
      data: {
        result: [
          {
            bvid: 'BV1demo',
            title: 'Demo Video',
            arcurl: 'https://www.bilibili.com/video/BV1demo',
          },
        ],
      },
    }),
  })

  assert.equal(result.page, 3)
  assert.equal(result.has_more, true)
  assert.equal(result.items.length, 1)
})

test('desktop all-site remote search interleaves lightweight site results before limiting', async () => {
  const javdbDocumentOptions = []
  const result = await searchRemoteVideos({
    query: 'demo',
    site: 'all',
    limit: 3,
    page: 1,
    buildCookieHeader,
    loadDocumentHtml: async (_url, options) => {
      javdbDocumentOptions.push(options)
      return `
        <div class="item">
          <a href="/v/javdb-demo">
            <img src="https://javdb.com/demo.jpg">
            <div class="video-title">JavDB 1</div>
          </a>
        </div>
      `
    },
    fetchImpl: async (url) => {
      const targetUrl = new URL(url)
      if (targetUrl.hostname.includes('bilibili')) {
        return jsonResponse({
          data: {
            result: [
              { bvid: 'BV1', title: 'Bilibili 1', arcurl: 'https://www.bilibili.com/video/BV1' },
              { bvid: 'BV2', title: 'Bilibili 2', arcurl: 'https://www.bilibili.com/video/BV2' },
              { bvid: 'BV3', title: 'Bilibili 3', arcurl: 'https://www.bilibili.com/video/BV3' },
            ],
          },
        })
      }
      if (targetUrl.hostname.includes('pornhub')) {
        return htmlResponse(`
          <li class="pcVideoListItem videoblock" data-video-vkey="ph-demo">
            <a href="/view_video.php?viewkey=ph-demo" title="Pornhub 1" data-title="Pornhub 1"></a>
          </li>
        `)
      }
      return htmlResponse('')
    },
  })

  assert.equal(result.items.length, 3)
  assert.deepEqual(result.items.map((item) => item.site), ['bilibili', 'pornhub', 'bilibili'])
  assert.equal(javdbDocumentOptions.length, 0)
  assert.deepEqual(result.sites, ['bilibili', 'youtube', 'pornhub', 'youporn'])
})

test('desktop remote search does not wait forever for a stalled site', async () => {
  const result = await searchRemoteVideos({
    query: 'demo',
    site: 'all',
    limit: 3,
    page: 1,
    providerTimeoutMs: 20,
    buildCookieHeader,
    loadDocumentHtml: async () => new Promise(() => {}),
    fetchImpl: async (url) => {
      const targetUrl = new URL(url)
      if (targetUrl.hostname.includes('bilibili')) {
        return jsonResponse({
          data: {
            result: [
              { bvid: 'BV1', title: 'Bilibili 1', arcurl: 'https://www.bilibili.com/video/BV1' },
            ],
          },
        })
      }
      return htmlResponse('')
    },
  })

  assert.deepEqual(result.items.map((item) => item.site), ['bilibili'])
  assert.equal(result.has_more, false)
  assert.equal(result.partial, false)
})

test('desktop all-site remote search returns initial ready sites without waiting for slow sites', async () => {
  const startedAt = Date.now()
  const result = await searchRemoteVideos({
    query: 'demo',
    site: 'all',
    limit: 3,
    page: 1,
    providerTimeoutMs: 10000,
    buildCookieHeader,
    loadDocumentHtml: async () => new Promise(() => {}),
    fetchImpl: async (url) => {
      const targetUrl = new URL(url)
      if (targetUrl.hostname.includes('bilibili')) {
        return jsonResponse({
          data: {
            result: [
              { bvid: 'BV1', title: 'Bilibili 1', arcurl: 'https://www.bilibili.com/video/BV1' },
            ],
          },
        })
      }
      await new Promise((resolve) => setTimeout(resolve, 10000))
      return htmlResponse('')
    },
  })

  assert.ok(Date.now() - startedAt < 5000)
  assert.deepEqual(result.items.map((item) => item.site), ['bilibili'])
  assert.equal(result.has_more, false)
  assert.equal(result.partial, true)
  assert.deepEqual(result.pending_sites, ['youtube', 'pornhub', 'youporn'])
})

test('desktop all-site remote search keeps later pages on lightweight sites', async () => {
  const javdbDocumentOptions = []
  await searchRemoteVideos({
    query: 'demo',
    site: 'all',
    limit: 3,
    page: 2,
    providerTimeoutMs: 20,
    buildCookieHeader,
    loadDocumentHtml: async (_url, options) => {
      javdbDocumentOptions.push(options)
      return loadJavdbDocumentHtml()
    },
    fetchImpl: async () => htmlResponse(''),
  })

  assert.equal(javdbDocumentOptions.length, 0)
})

test('desktop all-site remote search returns later ready pages without waiting for slow sites', async () => {
  const startedAt = Date.now()
  const result = await searchRemoteVideos({
    query: 'demo',
    site: 'all',
    limit: 3,
    page: 2,
    providerTimeoutMs: 10000,
    buildCookieHeader,
    loadDocumentHtml: async () => new Promise(() => {}),
    fetchImpl: async (url) => {
      const targetUrl = new URL(url)
      if (targetUrl.hostname.includes('bilibili')) {
        return jsonResponse({
          data: {
            result: [
              { bvid: 'BV2', title: 'Bilibili 2', arcurl: 'https://www.bilibili.com/video/BV2' },
            ],
          },
        })
      }
      await new Promise((resolve) => setTimeout(resolve, 10000))
      return htmlResponse('')
    },
  })

  assert.ok(Date.now() - startedAt < 5000)
  assert.deepEqual(result.items.map((item) => item.site), ['bilibili'])
  assert.equal(result.partial, true)
  assert.deepEqual(result.pending_sites, ['youtube', 'pornhub', 'youporn'])
})

test('desktop javdb site search requests automatic challenge solving window time', async () => {
  const documentOptions = []
  const result = await searchRemoteVideos({
    query: 'demo',
    site: 'javdb',
    limit: 5,
    page: 1,
    buildCookieHeader,
    fetchImpl: async () => htmlResponse(''),
    loadDocumentHtml: async (_url, options) => {
      documentOptions.push(options)
      return loadJavdbDocumentHtml()
    },
  })

  assert.equal(result.items.length, 1)
  assert.equal(result.items[0].site, 'javdb')
  assert.equal(documentOptions[0].timeoutMs, 30000)
  assert.equal(documentOptions[0].challengeTimeoutMs, 60000)
})

test('desktop bilibili remote channel returns profile and videos', async () => {
  const requestedUrls = []
  const documentUrls = []
  const result = await getRemoteChannel({
    site: 'bilibili',
    url: 'https://space.bilibili.com/12345',
    limit: 5,
    page: 2,
    buildCookieHeader,
    loadDocumentHtml: async (url, options = {}) => {
      documentUrls.push(url)
      assert.equal(typeof options.evaluatePage, 'function')
      return options.evaluatePage(async (script) => {
        if (!script.includes('/x/space/wbi/arc/search')) {
          return {
            dm_img_list: '[]',
            dm_img_str: 'img-demo',
            dm_cover_img_str: 'cover-demo',
            dm_img_inter: '{"demo":true}',
            w_webid: 'webid-demo',
          }
        }

        const match = script.match(/fetch\("([^"]+)"/)
        if (match?.[1]) requestedUrls.push(match[1])
        return {
          status: 200,
          text: JSON.stringify({
            code: 0,
            data: {
              page: {
                count: 20,
              },
              list: {
                vlist: [
                  {
                    bvid: 'BVchannel',
                    title: 'Channel Video',
                    pic: '//i0.hdslb.com/video.jpg',
                    length: '02:03',
                    created: 1700000000,
                  },
                ],
              },
            },
          }),
        }
      })
    },
    fetchImpl: async (url) => {
      requestedUrls.push(url)
      if (url.includes('/x/web-interface/card')) {
        return jsonResponse({
          data: {
            card: {
              name: 'Demo Uploader',
              face: '//i0.hdslb.com/avatar.jpg',
              sign: 'Demo channel',
            },
          },
        })
      }
      if (url.includes('/x/web-interface/nav')) {
        return jsonResponse({
          data: {
            wbi_img: {
              img_url: 'https://i0.hdslb.com/bfs/wbi/0123456789abcdef0123456789abcdef.png',
              sub_url: 'https://i0.hdslb.com/bfs/wbi/fedcba9876543210fedcba9876543210.png',
            },
          },
        })
      }
      throw new Error(`Unexpected request: ${url}`)
    },
  })

  assert.equal(result.site, 'bilibili')
  assert.equal(result.profile.name, 'Demo Uploader')
  assert.equal(result.profile.avatar, 'https://i0.hdslb.com/avatar.jpg')
  assert.equal(result.profile.description, 'Demo channel')
  assert.equal(result.items.length, 1)
  assert.equal(result.items[0].url, 'https://www.bilibili.com/video/BVchannel')
  assert.equal(result.items[0].duration, 123)
  assert.equal(result.has_more, true)
  assert.equal(documentUrls.length, 1)
  const videoRequestUrl = new URL(requestedUrls.find((url) => url.includes('/x/space/wbi/arc/search')))
  assert.equal(videoRequestUrl.searchParams.get('pn'), '2')
  assert.equal(videoRequestUrl.searchParams.get('dm_img_str'), 'img-demo')
  assert.equal(videoRequestUrl.searchParams.get('dm_cover_img_str'), 'cover-demo')
  assert.equal(videoRequestUrl.searchParams.get('dm_img_inter'), '{"demo":true}')
  assert.equal(videoRequestUrl.searchParams.get('w_webid'), 'webid-demo')
  assert.equal(videoRequestUrl.searchParams.has('w_rid'), true)
})

test('desktop youtube remote channel parses channel page videos', async () => {
  const initialData = {
    metadata: {
      channelMetadataRenderer: {
        title: 'Demo Channel',
        externalId: 'UCdemo',
        description: 'Demo description',
      },
    },
    contents: {
      twoColumnBrowseResultsRenderer: {
        tabs: [
          {
            tabRenderer: {
              content: {
                richGridRenderer: {
                  contents: [
                    {
                      continuationItemRenderer: {
                        continuationEndpoint: {
                          continuationCommand: { token: 'CONTINUATION_1' },
                        },
                      },
                    },
                    {
                      richItemRenderer: {
                        content: {
                          videoRenderer: {
                            videoId: 'abc123',
                            title: { runs: [{ text: 'Channel Video' }] },
                            thumbnail: { thumbnails: [{ url: 'https://i.ytimg.com/vi/abc123/hqdefault.jpg' }] },
                            lengthText: { simpleText: '03:04' },
                            publishedTimeText: { simpleText: '1 day ago' },
                          },
                        },
                      },
                    },
                  ],
                },
              },
            },
          },
        ],
      },
    },
  }

  let requestedUrl = ''
  const result = await getRemoteChannel({
    site: 'youtube',
    url: 'https://www.youtube.com/@demo',
    limit: 5,
    buildCookieHeader,
    fetchImpl: async (url) => {
      requestedUrl = url
      return htmlResponse(`
        <script>ytcfg.set({"INNERTUBE_API_KEY":"test-key","INNERTUBE_CONTEXT":{"client":{"clientName":"WEB","clientVersion":"1.0"}}});</script>
        <script>var ytInitialData = ${JSON.stringify(initialData)};</script>
      `)
    },
  })

  assert.equal(requestedUrl, 'https://www.youtube.com/@demo/videos')
  assert.equal(result.profile.id, 'UCdemo')
  assert.equal(result.profile.name, 'Demo Channel')
  assert.equal(result.profile.description, 'Demo description')
  assert.equal(result.items.length, 1)
  assert.equal(result.items[0].url, 'https://www.youtube.com/watch?v=abc123')
  assert.equal(result.items[0].duration, 184)
  assert.deepEqual(result.items[0].subscriptions, [result.profile])
  assert.equal(result.has_more, true)
  assert.equal(result.next_cursor.continuation, 'CONTINUATION_1')
})

test('desktop youtube remote channel parses lockup view model videos', async () => {
  const initialData = {
    metadata: {
      channelMetadataRenderer: {
        title: 'Modern Channel',
        externalId: 'UCmodern',
      },
    },
    contents: {
      richGridRenderer: {
        contents: [
          {
            richItemRenderer: {
              content: {
                lockupViewModel: {
                  contentImage: {
                    thumbnailViewModel: {
                      image: {
                        sources: [{ url: 'https://i.ytimg.com/vi/lock123/hqdefault.jpg' }],
                      },
                      overlays: [
                        {
                          thumbnailBottomOverlayViewModel: {
                            badges: [
                              { thumbnailBadgeViewModel: { text: '01:17' } },
                            ],
                          },
                        },
                      ],
                    },
                  },
                  metadata: {
                    lockupMetadataViewModel: {
                      title: { content: 'Modern Channel Video' },
                      metadata: {
                        contentMetadataViewModel: {
                          metadataRows: [
                            {
                              metadataParts: [
                                { text: { content: '2.5K views' } },
                                { text: { content: '8 days ago' } },
                              ],
                            },
                          ],
                        },
                      },
                    },
                  },
                  rendererContext: {
                    commandContext: {
                      onTap: {
                        innertubeCommand: {
                          watchEndpoint: { videoId: 'lock123' },
                        },
                      },
                    },
                  },
                },
              },
            },
          },
        ],
      },
    },
  }

  const result = await getRemoteChannel({
    site: 'youtube',
    url: 'https://www.youtube.com/@modern',
    limit: 5,
    buildCookieHeader,
    fetchImpl: async () => htmlResponse(`
      <script>ytcfg.set({"INNERTUBE_API_KEY":"test-key","INNERTUBE_CONTEXT":{"client":{"clientName":"WEB","clientVersion":"1.0"}}});</script>
      <script>var ytInitialData = ${JSON.stringify(initialData)};</script>
    `),
  })

  assert.equal(result.profile.id, 'UCmodern')
  assert.equal(result.items.length, 1)
  assert.equal(result.items[0].title, 'Modern Channel Video')
  assert.equal(result.items[0].url, 'https://www.youtube.com/watch?v=lock123')
  assert.equal(result.items[0].duration, 77)
  assert.equal(result.items[0].published_text, '8 days ago')
})

test('desktop youtube remote channel loads continuation videos', async () => {
  const requests = []
  const result = await getRemoteChannel({
    site: 'youtube',
    url: 'https://www.youtube.com/@demo',
    limit: 5,
    page: 2,
    cursor: {
      continuation: 'CONTINUATION_1',
      api_key: 'test-key',
      context: { client: { clientName: 'WEB', clientVersion: '1.0' } },
    },
    profile: {
      id: 'UCdemo',
      name: 'Demo Channel',
      url: 'https://www.youtube.com/@demo',
      avatar: '',
    },
    buildCookieHeader,
    fetchImpl: async (url, options = {}) => {
      requests.push({ url, options })
      return jsonResponse({
        onResponseReceivedActions: [
          {
            appendContinuationItemsAction: {
              continuationItems: [
                {
                  richItemRenderer: {
                    content: {
                      videoRenderer: {
                        videoId: 'def456',
                        title: { runs: [{ text: 'Continuation Video' }] },
                        thumbnail: { thumbnails: [{ url: 'https://i.ytimg.com/vi/def456/hqdefault.jpg' }] },
                        lengthText: { simpleText: '04:05' },
                      },
                    },
                  },
                },
                {
                  continuationItemRenderer: {
                    continuationEndpoint: {
                      continuationCommand: { token: 'CONTINUATION_2' },
                    },
                  },
                },
              ],
            },
          },
        ],
      })
    },
  })

  assert.equal(requests[0].url, 'https://www.youtube.com/youtubei/v1/browse?key=test-key')
  assert.equal(requests[0].options.method, 'POST')
  assert.equal(JSON.parse(requests[0].options.body).continuation, 'CONTINUATION_1')
  assert.equal(result.items.length, 1)
  assert.equal(result.items[0].url, 'https://www.youtube.com/watch?v=def456')
  assert.equal(result.items[0].duration, 245)
  assert.equal(result.has_more, true)
  assert.equal(result.next_cursor.continuation, 'CONTINUATION_2')
})
