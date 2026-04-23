import {
  DEFAULT_USER_AGENT,
  extractJsonArrayFromObjectLiteral,
  fetchPageHtml,
  findObjectLiteralAfterPattern,
  getCachedPayload,
  mergeCookieHeaders,
  normalizeTargetUrl,
  pickBestDefinition,
  safeInt,
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

const buildQualities = (definitions) => {
  const qualities = []
  const seen = new Set()

  for (const item of Array.isArray(definitions) ? definitions : []) {
    const format = String(item?.format || '').toLowerCase()
    if (format !== 'hls' || !safeUrl(item?.videoUrl)) {
      continue
    }

    const height = safeInt(item?.height || item?.quality) || null
    const width = safeInt(item?.width) || null
    const qualityId = `ph-hls:${width || 0}x${height || 0}`
    if (seen.has(qualityId)) {
      continue
    }
    seen.add(qualityId)

    qualities.push({
      id: qualityId,
      value: qualityId,
      label: height ? `${height}p` : qualityId,
      height,
      bandwidth: null,
      codec: null,
    })
  }

  qualities.sort((left, right) => safeInt(right.height) - safeInt(left.height))
  return qualities
}

const mapPlaybackPayload = (targetUrl, definitions) => {
  const hlsDefinition = pickBestDefinition(definitions, 'hls')
  if (hlsDefinition?.videoUrl) {
    const qualities = buildQualities(definitions)
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
