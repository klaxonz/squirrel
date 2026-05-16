import assert from 'node:assert/strict'
import test from 'node:test'

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

  const items = await searchYouTubeVideos({
    query: 'demo',
    limit: 5,
    buildCookieHeader,
    fetchImpl: async () => htmlResponse(`<script>var ytInitialData = ${JSON.stringify(initialData)};</script>`),
  })

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
})

test('desktop youtube remote search does not repeat first page for page requests', async () => {
  const items = await searchYouTubeVideos({
    query: 'demo',
    limit: 5,
    page: 2,
    buildCookieHeader,
    fetchImpl: async () => {
      throw new Error('fetch should not be called for page 2')
    },
  })

  assert.deepEqual(items, [])
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

test('desktop remote search interleaves all site results before limiting', async () => {
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
  assert.deepEqual(result.items.map((item) => item.site), ['bilibili', 'javdb', 'pornhub'])
  assert.equal(javdbDocumentOptions[0].timeoutMs, 30000)
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
  assert.ok(result.errors.some((message) => message.includes('javdb search timed out')))
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
