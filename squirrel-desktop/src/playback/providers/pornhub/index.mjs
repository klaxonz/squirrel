import {
  DEFAULT_USER_AGENT,
  buildHlsQualities,
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

const PORNHUB_ORIGIN = 'https://www.pornhub.com'
const PORNHUB_REFERER = `${PORNHUB_ORIGIN}/`
const AGE_GATE_COOKIE_HEADER = 'age_verified=1; accessAgeDisclaimerPH=1; accessAgeDisclaimerUK=1; accessPH=1'

const buildCookieHeader = (cookie) => {
  return mergeCookieHeaders(AGE_GATE_COOKIE_HEADER, cookie)
}

const extractMediaDefinitions = (htmlText) => {
  const flashvars = findObjectLiteralAfterPattern(htmlText, /var\s+flashvars_\d+\s*=/i)
  const definitions = extractJsonArrayFromObjectLiteral(flashvars, 'mediaDefinitions')
  if (definitions?.length) {
    return definitions
  }

  const directMatch = htmlText.match(/mediaDefinitions"\s*:\s*(\[[\s\S]*?\])\s*,\s*"isVertical"/i)
  if (directMatch?.[1]) {
    try {
      return JSON.parse(directMatch[1])
    } catch {
      return []
    }
  }

  return []
}

const mapPlaybackPayload = (targetUrl, definitions) => {
  const hlsDefinition = pickBestDefinition(definitions, 'hls')
  if (hlsDefinition?.videoUrl) {
    const qualities = buildHlsQualities(definitions, 'ph-hls')
    return {
      stream_type: 'hls',
      video_url: hlsDefinition.videoUrl,
      audio_url: null,
      mpd_url: null,
      mpd_content: null,
      qualities: qualities.length > 0 ? qualities : null,
      default_quality_id: qualities[0]?.id || null,
      supports_manual_quality: qualities.length > 1,
      metadata: {
        provider: 'pornhub',
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
        provider: 'pornhub',
        url: targetUrl,
      },
    }
  }

  throw new Error('Pornhub provider did not return a playable payload')
}

export async function resolvePornhubPlayback(targetUrl, { cookie = '', forceRefresh = false, fetchImpl } = {}) {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    throw new Error('Invalid Pornhub URL')
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
    referer: PORNHUB_REFERER,
    origin: PORNHUB_ORIGIN,
    userAgent: DEFAULT_USER_AGENT,
    fetchImpl,
  })
  const definitions = extractMediaDefinitions(htmlText)
  const payload = mapPlaybackPayload(normalizedUrl, definitions)
  setCachedPayload(cacheKey, payload)
  return payload
}
