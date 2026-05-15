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
                    ownerText: { runs: [{ text: 'Demo Channel' }] },
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
        <var class="duration">04:05</var>
      </li>
    `),
  })

  assert.equal(items.length, 1)
  assert.equal(items[0].site, 'pornhub')
  assert.equal(items[0].title, 'Demo PH')
  assert.equal(items[0].duration, 245)
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
      </article>
    `),
  })

  assert.equal(items.length, 1)
  assert.equal(items[0].site, 'youporn')
  assert.equal(items[0].url, 'https://www.youporn.com/watch/123/demo/')
  assert.equal(items[0].thumbnail, 'https://fi.ypncdn.com/demo.jpg')
  assert.equal(items[0].duration, 306)
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
