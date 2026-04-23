import {
  DEFAULT_USER_AGENT,
  extractJsonArrayFromObjectLiteral,
  fetchPageHtml,
  findObjectLiteralAfterPattern,
  getCachedPayload,
  mergeCookieHeaders,
  normalizeTargetUrl,
  pickBestDefinition,
  safeUrl,
  setCachedPayload,
} from '../shared/adult-page.mjs'

const YOUPORN_ORIGIN = 'https://www.youporn.com'
const YOUPORN_REFERER = `${YOUPORN_ORIGIN}/`
const AGE_GATE_COOKIE_HEADER = 'showAgeDisclaimer=1; access=1; accessPH=1'

const buildCookieHeader = (cookie) => {
  return mergeCookieHeaders(AGE_GATE_COOKIE_HEADER, cookie)
}

const extractMediaDefinitions = (htmlText) => {
  const playervars = findObjectLiteralAfterPattern(htmlText, /playervars\s*:/i)
  const definitions = extractJsonArrayFromObjectLiteral(playervars, 'mediaDefinitions')
  if (definitions?.length) {
    return definitions
  }

  const directMatch = htmlText.match(/"mediaDefinitions"\s*:\s*(\[[\s\S]*?\])\s*,\s*"video_unavailable_country"/i)
  if (directMatch?.[1]) {
    try {
      return JSON.parse(directMatch[1])
    } catch {
      return []
    }
  }

  return []
}

const fetchRemoteDefinitions = async (targetUrl, cookie, fetchImpl = globalThis.fetch) => {
  const response = await fetchImpl(targetUrl, {
    headers: {
      'Accept-Language': 'en-US,en;q=0.9',
      'User-Agent': DEFAULT_USER_AGENT,
      Referer: YOUPORN_REFERER,
      Origin: YOUPORN_ORIGIN,
      Cookie: buildCookieHeader(cookie),
    },
    redirect: 'follow',
  })

  if (!response.ok) {
    throw new Error(`YouPorn media endpoint failed with HTTP ${response.status}`)
  }

  const text = await response.text()
  try {
    const payload = JSON.parse(text)
    return Array.isArray(payload) ? payload : []
  } catch {
    return []
  }
}

const expandMediaDefinitions = async (definitions, cookie, fetchImpl) => {
  const expanded = []

  for (const item of Array.isArray(definitions) ? definitions : []) {
    const format = String(item?.format || '').toLowerCase()
    const videoUrl = safeUrl(item?.videoUrl)
    if (!videoUrl) {
      continue
    }

    if (videoUrl.startsWith(`${YOUPORN_ORIGIN}/media/`)) {
      const remoteDefinitions = await fetchRemoteDefinitions(videoUrl, cookie, fetchImpl)
      if (remoteDefinitions.length > 0) {
        for (const remoteItem of remoteDefinitions) {
          expanded.push({
            ...remoteItem,
            format: String(remoteItem?.format || format).toLowerCase(),
          })
        }
        continue
      }
    }

    expanded.push(item)
  }

  return expanded
}

const mapPlaybackPayload = (targetUrl, definitions) => {
  const hlsDefinition = pickBestDefinition(definitions, 'hls')
  if (hlsDefinition?.videoUrl) {
    return {
      stream_type: 'hls',
      video_url: hlsDefinition.videoUrl,
      audio_url: null,
      mpd_url: null,
      mpd_content: null,
      qualities: null,
      default_quality_id: null,
      supports_manual_quality: false,
      metadata: {
        provider: 'youporn',
        url: targetUrl,
      },
    }
  }

  const mp4Definition = pickBestDefinition(definitions, 'mp4')
  if (mp4Definition?.videoUrl) {
    return {
      stream_type: 'progressive',
      video_url: mp4Definition.videoUrl,
      audio_url: null,
      mpd_url: null,
      mpd_content: null,
      qualities: null,
      default_quality_id: null,
      supports_manual_quality: false,
      metadata: {
        provider: 'youporn',
        url: targetUrl,
      },
    }
  }

  throw new Error('YouPorn provider did not return a playable payload')
}

export async function resolveYouPornPlayback(targetUrl, { cookie = '', forceRefresh = false, fetchImpl } = {}) {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    throw new Error('Invalid YouPorn URL')
  }

  const cacheKey = `${normalizedUrl}|cookie=${cookie ? '1' : '0'}`
  if (!forceRefresh) {
    const cached = getCachedPayload(cacheKey)
    if (cached) {
      return cached
    }
  }

  const htmlText = await fetchPageHtml(normalizedUrl, {
    cookie: buildCookieHeader(cookie),
    referer: YOUPORN_REFERER,
    origin: YOUPORN_ORIGIN,
    userAgent: DEFAULT_USER_AGENT,
    fetchImpl,
  })
  const definitions = (await expandMediaDefinitions(extractMediaDefinitions(htmlText), cookie, fetchImpl))
    .filter((item) => safeUrl(item?.videoUrl))
  const payload = mapPlaybackPayload(normalizedUrl, definitions)
  setCachedPayload(cacheKey, payload)
  return payload
}
