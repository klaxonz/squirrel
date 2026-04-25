import assert from 'node:assert/strict'
import test from 'node:test'

import { resolvePornhubPlayback } from '../src/playback/providers/pornhub/index.mjs'
import { resolveYouPornPlayback } from '../src/playback/providers/youporn/index.mjs'

const jsonResponse = (payload) => ({
  ok: true,
  status: 200,
  async text() {
    return JSON.stringify(payload)
  },
})

const htmlResponse = (html) => ({
  ok: true,
  status: 200,
  async text() {
    return html
  },
})

const waitFor = async (predicate, message) => {
  const deadline = Date.now() + 1000
  while (!predicate()) {
    if (Date.now() > deadline) {
      throw new Error(message)
    }
    await new Promise((resolve) => setTimeout(resolve, 0))
  }
}

test('desktop pornhub provider exposes sorted hls qualities', async () => {
  const html = `
    <script>
      var flashvars_123 = {
        "mediaDefinitions": [
          { "format": "hls", "quality": "720", "height": 720, "width": 1280, "videoUrl": "https://cdn.example.test/720.m3u8" },
          { "format": "hls", "quality": "1080", "height": 1080, "width": 1920, "videoUrl": "https://cdn.example.test/1080.m3u8" }
        ]
      };
    </script>
  `
  const payload = await resolvePornhubPlayback('https://www.pornhub.com/view_video.php?viewkey=abc123', {
    forceRefresh: true,
    fetchImpl: async () => htmlResponse(html),
  })

  assert.equal(payload.stream_type, 'hls')
  assert.equal(payload.video_url, 'https://cdn.example.test/1080.m3u8')
  assert.equal(payload.default_quality_id, 'ph-hls:1920x1080')
  assert.deepEqual(payload.qualities.map((item) => item.label), ['1080p', '720p'])
  assert.equal(payload.supports_manual_quality, true)
})

test('desktop youporn provider expands remote definitions in parallel and exposes hls qualities', async () => {
  const html = `
    <script>
      window.initials = {
        playervars: {
          "mediaDefinitions": [
            { "format": "hls", "videoUrl": "https://www.youporn.com/media/a" },
            { "format": "hls", "videoUrl": "https://www.youporn.com/media/b" }
          ]
        }
      };
    </script>
  `
  const requestStarts = []
  const releaseRemoteResponses = []
  let activeRemoteRequests = 0
  let peakRemoteRequests = 0

  const fetchImpl = async (targetUrl) => {
    const url = String(targetUrl)
    if (url.includes('/watch/')) {
      return htmlResponse(html)
    }

    requestStarts.push(url)
    activeRemoteRequests += 1
    peakRemoteRequests = Math.max(peakRemoteRequests, activeRemoteRequests)
    await new Promise((resolve) => releaseRemoteResponses.push(resolve))
    activeRemoteRequests -= 1

    if (url.endsWith('/a')) {
      return jsonResponse([{ format: 'hls', height: 720, width: 1280, videoUrl: 'https://cdn.example.test/720.m3u8' }])
    }
    return jsonResponse([{ format: 'hls', height: 1080, width: 1920, videoUrl: 'https://cdn.example.test/1080.m3u8' }])
  }

  const payloadPromise = resolveYouPornPlayback('https://www.youporn.com/watch/123/example/', {
    forceRefresh: true,
    fetchImpl,
  })

  await waitFor(() => requestStarts.length >= 2, 'YouPorn remote definitions were not requested')
  assert.equal(peakRemoteRequests, 2)
  releaseRemoteResponses.splice(0).forEach((resolve) => resolve())

  const payload = await payloadPromise
  assert.equal(payload.stream_type, 'hls')
  assert.equal(payload.video_url, 'https://cdn.example.test/1080.m3u8')
  assert.equal(payload.default_quality_id, 'yp-hls:1920x1080')
  assert.deepEqual(payload.qualities.map((item) => item.label), ['1080p', '720p'])
  assert.equal(payload.supports_manual_quality, true)
})
