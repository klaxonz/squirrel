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

test('desktop pornhub provider does not reuse cached payload across cookie sessions', async () => {
  const anonymousHtml = `
    <script>
      var flashvars_123 = {
        "mediaDefinitions": [
          { "format": "hls", "quality": "480", "height": 480, "width": 854, "videoUrl": "https://cdn.example.test/anonymous.m3u8" }
        ]
      };
    </script>
  `
  const sessionHtml = `
    <script>
      var flashvars_123 = {
        "mediaDefinitions": [
          { "format": "hls", "quality": "1080", "height": 1080, "width": 1920, "videoUrl": "https://cdn.example.test/session.m3u8" }
        ]
      };
    </script>
  `
  const requests = []
  const fetchImpl = async (_targetUrl, options = {}) => {
    const cookie = String(options?.headers?.Cookie || '')
    requests.push(cookie)
    return htmlResponse(cookie.includes('session=demo') ? sessionHtml : anonymousHtml)
  }

  const anonymousPayload = await resolvePornhubPlayback(
    'https://www.pornhub.com/view_video.php?viewkey=session-cache',
    { forceRefresh: true, fetchImpl },
  )
  const sessionPayload = await resolvePornhubPlayback(
    'https://www.pornhub.com/view_video.php?viewkey=session-cache',
    { cookie: 'session=demo', fetchImpl },
  )

  assert.equal(anonymousPayload.video_url, 'https://cdn.example.test/anonymous.m3u8')
  assert.equal(sessionPayload.video_url, 'https://cdn.example.test/session.m3u8')
  assert.equal(requests.length, 2)
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
  assert.equal(payload.default_quality_id, 'yp-hls:1920x1080:4000000')
  assert.deepEqual(payload.qualities.map((item) => item.label), ['1080p', '720p'])
  assert.deepEqual(payload.qualities.map((item) => item.src), [
    'https://cdn.example.test/1080.m3u8',
    'https://cdn.example.test/720.m3u8',
  ])
  assert.equal(payload.supports_manual_quality, true)
})

test('desktop youporn provider exposes direct hls quality sources from media definitions', async () => {
  const html = `
    <script>
      window.initials = {
        playervars: {
          "mediaDefinitions": [
            { "format": "hls", "quality": "720", "height": 720, "width": 1280, "videoUrl": "https://cdn.example.test/720/index.m3u8" },
            { "format": "hls", "quality": "1080", "height": 1080, "width": 1920, "videoUrl": "https://cdn.example.test/1080/index.m3u8" }
          ]
        }
      };
    </script>
  `
  const requestedUrls = []

  const payload = await resolveYouPornPlayback('https://www.youporn.com/watch/123/synthesized-master/', {
    forceRefresh: true,
    fetchImpl: async (targetUrl) => {
      const url = String(targetUrl)
      requestedUrls.push(url)
      if (url.includes('/watch/')) {
        return htmlResponse(html)
      }
      throw new Error(`Unexpected request: ${url}`)
    },
  })

  assert.equal(payload.stream_type, 'hls')
  assert.equal(payload.video_url, 'https://cdn.example.test/1080/index.m3u8')
  assert.equal(payload.default_quality_id, 'yp-hls:1920x1080:4000000')
  assert.deepEqual(payload.qualities.map((item) => item.label), ['1080p', '720p'])
  assert.deepEqual(requestedUrls, ['https://www.youporn.com/watch/123/synthesized-master/'])
  assert.deepEqual(payload.qualities.map((item) => item.src), [
    'https://cdn.example.test/1080/index.m3u8',
    'https://cdn.example.test/720/index.m3u8',
  ])
  assert.equal(payload.supports_manual_quality, true)
})

test('desktop youporn provider derives quality labels from media urls when dimensions are player sized', async () => {
  const html = `
    <script>
      window.initials = {
        playervars: {
          "mediaDefinitions": [
            { "format": "hls", "height": 404, "width": 720, "videoUrl": "https://cdn.example.test/video_720P_4000K_demo.mp4/master.m3u8" },
            { "format": "hls", "height": 404, "width": 720, "videoUrl": "https://cdn.example.test/video_1080P_4000K_demo.mp4/master.m3u8" },
            { "format": "hls", "height": 404, "width": 720, "videoUrl": "https://cdn.example.test/video_480P_2000K_demo.mp4/master.m3u8" }
          ]
        }
      };
    </script>
  `

  const payload = await resolveYouPornPlayback('https://www.youporn.com/watch/123/url-quality/', {
    forceRefresh: true,
    fetchImpl: async (targetUrl) => {
      const url = String(targetUrl)
      if (url.includes('/watch/')) {
        return htmlResponse(html)
      }
      throw new Error(`Unexpected request: ${url}`)
    },
  })

  assert.equal(payload.video_url, 'https://cdn.example.test/video_1080P_4000K_demo.mp4/master.m3u8')
  assert.deepEqual(payload.qualities.map((item) => item.label), ['1080p', '720p', '480p'])
  assert.deepEqual(payload.qualities.map((item) => item.src), [
    'https://cdn.example.test/video_1080P_4000K_demo.mp4/master.m3u8',
    'https://cdn.example.test/video_720P_4000K_demo.mp4/master.m3u8',
    'https://cdn.example.test/video_480P_2000K_demo.mp4/master.m3u8',
  ])
})

test('desktop youporn provider expands current you-porn media definitions', async () => {
  const html = `
    <script>
      window.initials = {
        playervars: {
          "mediaDefinitions": [
            { "format": "hls", "videoUrl": "https://www.you-porn.com/media/a" }
          ]
        }
      };
    </script>
  `
  const requestedUrls = []
  const origins = []
  const referers = []

  const payload = await resolveYouPornPlayback('https://www.you-porn.com/watch/123/current-domain/', {
    forceRefresh: true,
    fetchImpl: async (targetUrl, options = {}) => {
      const url = String(targetUrl)
      requestedUrls.push(url)
      origins.push(options?.headers?.Origin)
      referers.push(options?.headers?.Referer)
      if (url.includes('/watch/')) {
        return htmlResponse(html)
      }
      if (url.includes('/media/a')) {
        return jsonResponse([
          { format: 'hls', height: 720, width: 1280, videoUrl: 'https://cdn.example.test/720.m3u8' },
          { format: 'hls', height: 1080, width: 1920, videoUrl: 'https://cdn.example.test/1080.m3u8' },
        ])
      }
      throw new Error(`Unexpected request: ${url}`)
    },
  })

  assert.equal(requestedUrls.includes('https://www.you-porn.com/media/a'), true)
  assert.equal(origins.every((origin) => origin === 'https://www.you-porn.com'), true)
  assert.equal(referers.every((referer) => referer === 'https://www.you-porn.com/'), true)
  assert.equal(payload.video_url, 'https://cdn.example.test/1080.m3u8')
  assert.deepEqual(payload.qualities.map((item) => item.label), ['1080p', '720p'])
})
