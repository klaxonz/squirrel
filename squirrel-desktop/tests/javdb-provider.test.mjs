import assert from 'node:assert/strict'
import test from 'node:test'

import { resolveJavdbMetadata, resolveJavdbPlayback, formatStreamUrl } from '../src/playback/providers/javdb/index.mjs'

const streamParts = 'm3u8|one|two|three|four|five|com|example|cdn|videos|https|video|master|playlist|source'

test('desktop javdb provider resolves missav hls stream from javdb detail page', async () => {
  const requestedUrls = []
  const payload = await resolveJavdbPlayback('https://javdb.com/v/demo', {
    forceRefresh: true,
    loadDocumentHtml: async (url) => {
      requestedUrls.push(url)
      if (url === 'https://javdb.com/v/demo') {
        return '<div class="title"><strong>ABP-123</strong><strong>Demo Title</strong></div>'
      }
      if (url === 'https://missav.ai/abp-123') {
        return `<script>'${streamParts}'</script>`
      }
      throw new Error(`Unexpected document URL: ${url}`)
    },
  })

  assert.deepEqual(requestedUrls, [
    'https://javdb.com/v/demo',
    'https://missav.ai/abp-123',
  ])
  assert.equal(payload.stream_type, 'hls')
  assert.equal(payload.video_url, 'https://videos.cdn.example.com/five-four-three-two-one/master/video.m3u8')
  assert.equal(payload.metadata.video_no, 'ABP-123')
  assert.equal(payload.metadata.referer, 'https://missav.ai/abp-123')
  assert.equal(payload.metadata.video, undefined)
})

test('desktop javdb provider uses supplied title before loading javdb detail', async () => {
  const requestedUrls = []
  const payload = await resolveJavdbPlayback('https://javdb.com/v/title-demo', {
    forceRefresh: true,
    title: 'SSIS-001 Demo Title',
    loadDocumentHtml: async (url) => {
      requestedUrls.push(url)
      if (url === 'https://missav.ai/ssis-001') {
        return `<script>'${streamParts}'</script>`
      }
      throw new Error(`Unexpected document URL: ${url}`)
    },
  })

  assert.deepEqual(requestedUrls, ['https://missav.ai/ssis-001'])
  assert.equal(payload.metadata.video_no, 'SSIS-001')
})

test('desktop javdb provider follows missav search result when direct detail has no stream', async () => {
  const requestedUrls = []
  const payload = await resolveJavdbPlayback('https://javdb.com/v/search-demo', {
    forceRefresh: true,
    title: 'ABF-304 Demo Title',
    loadDocumentHtml: async (url) => {
      requestedUrls.push(url)
      if (url === 'https://missav.ai/abf-304') {
        return '<html><body>No stream here</body></html>'
      }
      if (url === 'https://missav.ai/search/ABF-304') {
        return '<div class="thumbnail"><a href="/abf-304-alt">alt</a></div>'
      }
      if (url === 'https://missav.ai/abf-304-alt') {
        return `<script>'${streamParts}'</script>`
      }
      throw new Error(`Unexpected document URL: ${url}`)
    },
  })

  assert.deepEqual(requestedUrls, [
    'https://missav.ai/abf-304',
    'https://missav.ai/search/ABF-304',
    'https://missav.ai/abf-304-alt',
  ])
  assert.equal(payload.metadata.referer, 'https://missav.ai/abf-304-alt')
})

test('desktop javdb provider resolves metadata from javdb detail separately', async () => {
  const metadata = await resolveJavdbMetadata('https://javdb.com/v/demo', {
    loadDocumentHtml: async (url) => {
      assert.equal(url, 'https://javdb.com/v/demo')
      return `
        <div class="title"><strong>ABP-123</strong><strong>Demo Title</strong></div>
        <img class="video-cover" src="/covers/demo.jpg">
        <a href="/actors/censored">Censored</a>
        <div class="movie-panel-info">
          <div class="panel-block"><strong>Released Date:</strong> <span>2026-01-02</span></div>
          <div class="panel-block"><strong>Duration:</strong> <span>123 min</span></div>
          <div class="panel-block"><strong>演員:</strong> <a href="/actors/demo-actor">Demo Actor</a></div>
        </div>
      `
    },
  })

  assert.deepEqual(metadata, {
    title: 'ABP-123 Demo Title',
    thumbnail: 'https://javdb.com/covers/demo.jpg',
    publish_date: '2026-01-02',
    duration: 7380,
    actors: [{
      id: 'demo-actor',
      type: 'ACTOR',
      name: 'Demo Actor',
      url: 'https://javdb.com/actors/demo-actor',
      avatar: '',
      is_nsfw: true,
    }],
  })
})

test('desktop javdb provider extracts packed missav stream metadata', () => {
  assert.equal(
    formatStreamUrl(streamParts),
    'https://videos.cdn.example.com/five-four-three-two-one/master/video.m3u8',
  )
})
