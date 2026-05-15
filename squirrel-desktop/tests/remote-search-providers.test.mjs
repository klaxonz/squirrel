import assert from 'node:assert/strict'
import test from 'node:test'

import { searchBilibiliVideos } from '../src/search/providers/bilibili.mjs'
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

test('desktop bilibili remote search maps api results', async () => {
  const items = await searchBilibiliVideos({
    query: 'demo',
    limit: 5,
    buildCookieHeader,
    fetchImpl: async () => jsonResponse({
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
    }),
  })

  assert.equal(items.length, 1)
  assert.equal(items[0].site, 'bilibili')
  assert.equal(items[0].title, 'Demo Video')
  assert.equal(items[0].duration, 62)
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
      <div class="video-box">
        <img data-src="https://fi.ypncdn.com/demo.jpg" alt="Demo YP">
        <span class="duration">05:06</span>
        <a href="/watch/123/demo/" title="Demo YP">Demo YP</a>
      </div>
    `),
  })

  assert.equal(items.length, 1)
  assert.equal(items[0].site, 'youporn')
  assert.equal(items[0].url, 'https://www.youporn.com/watch/123/demo/')
  assert.equal(items[0].duration, 306)
})

test('desktop javdb remote search parses movie items', async () => {
  const items = await searchJavdbVideos({
    query: 'demo',
    limit: 5,
    buildCookieHeader,
    fetchImpl: async () => htmlResponse(`
      <div class="item">
        <a href="/v/demo">
          <img src="https://javdb.com/demo.jpg">
          <div class="video-title">Demo JAVDB</div>
          <div class="score">7.5</div>
        </a>
      </div>
    `),
  })

  assert.equal(items.length, 1)
  assert.equal(items[0].site, 'javdb')
  assert.equal(items[0].title, 'Demo JAVDB')
  assert.equal(items[0].url, 'https://javdb.com/v/demo')
})
