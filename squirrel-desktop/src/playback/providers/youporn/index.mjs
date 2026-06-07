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

const YOUPORN_MEDIA_PATH_PATTERN = /^https:\/\/www\.(?:youporn|you-porn)\.com\/media\//i
const AGE_GATE_COOKIE_HEADER = 'showAgeDisclaimer=1; access=1; accessPH=1'

const extractPageTitle = (htmlText) => {
  const ogTitle = htmlText.match(/<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']+)["']/i)?.[1]
  return ogTitle ? ogTitle.trim() : String(htmlText.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1] || '').replace(/\s*[-|]\s*\S+\s*$/, '').trim()
}

const extractPageThumbnail = (htmlText) => {
  const ogImage = htmlText.match(/<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']/i)?.[1]
  if (ogImage) return ogImage.trim()
  const jsonLdThumb = htmlText.match(/"thumbnailUrl"\s*:\s*"([^"]+)"/i)?.[1]
  return jsonLdThumb ? jsonLdThumb.trim() : ''
}

const extractYpUploaderName = (htmlText) => {
  const jsonLdScripts = htmlText.match(/<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi) || []
  for (const script of jsonLdScripts) {
    const authorMatch = script.match(/"author"\s*:\s*"([^"]+)"/i)
    if (authorMatch?.[1] && authorMatch[1].trim()) return authorMatch[1].trim()
  }
  return null
}

const extractYpUploaderUrl = (htmlText, targetUrl) => {
  const match = htmlText.match(/<a\b[^>]*href=["']((?:\/user\/|\/pornstar\/|\/channel\/)[^"']+)["'][^>]*>/i)
  if (match?.[1]) return new URL(match[1], new URL(targetUrl).origin).toString()
  return null
}

const buildCookieHeader = (cookie) => {
  return mergeCookieHeaders(AGE_GATE_COOKIE_HEADER, cookie)
}

const buildRequestContext = (targetUrl) => {
  const url = new URL(targetUrl)
  return {
    origin: url.origin,
    referer: `${url.origin}/`,
  }
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
      console.debug('[squirrel-desktop] youporn: extractMediaDefinitions JSON parse failed')
      return []
    }
  }

  return []
}

const fetchRemoteDefinitions = async (targetUrl, cookie, requestContext, fetchImpl = globalThis.fetch) => {
  const response = await fetchImpl(targetUrl, {
    headers: {
      'Accept-Language': 'en-US,en;q=0.9',
      'User-Agent': DEFAULT_USER_AGENT,
      Referer: requestContext.referer,
      Origin: requestContext.origin,
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
    console.debug('[squirrel-desktop] youporn: fetchRemoteDefinitions JSON parse failed')
    return []
  }
}

const expandMediaDefinitions = async (definitions, cookie, requestContext, fetchImpl) => {
  const items = Array.isArray(definitions) ? definitions : []
  const expandedGroups = await Promise.all(items.map(async (item) => {
    const format = String(item?.format || '').toLowerCase()
    const videoUrl = safeUrl(item?.videoUrl)
    if (!videoUrl) {
      return []
    }

    if (YOUPORN_MEDIA_PATH_PATTERN.test(videoUrl)) {
      const remoteDefinitions = await fetchRemoteDefinitions(videoUrl, cookie, requestContext, fetchImpl)
      if (remoteDefinitions.length > 0) {
        return remoteDefinitions.map((remoteItem) => ({
          ...remoteItem,
          format: String(remoteItem?.format || format).toLowerCase(),
        }))
      }
    }

    return [item]
  }))

  return expandedGroups.flat()
}

const parseQualityHeight = (definition) => {
  const explicitQuality = safeInt(definition?.quality)
  if (explicitQuality > 0) {
    return explicitQuality
  }

  const urlMatch = safeUrl(definition?.videoUrl).match(/(?:^|[_/-])(\d{3,4})P(?:[_/-]|$)/i)
  if (urlMatch?.[1]) {
    return safeInt(urlMatch[1])
  }

  return safeInt(definition?.height)
}

const parseQualityBandwidth = (definition) => {
  const explicit = safeInt(definition?.bandwidth || definition?.bitrate)
  if (explicit > 0) {
    return explicit
  }

  const urlMatch = safeUrl(definition?.videoUrl).match(/(?:^|[_/-])(\d{3,5})K(?:[_/-]|$)/i)
  if (urlMatch?.[1]) {
    return safeInt(urlMatch[1]) * 1000
  }

  return 0
}

const estimateWidth = (definition, height) => {
  const width = safeInt(definition?.width)
  if (width > height) {
    return width
  }
  return height > 0 ? Math.round((height * 16) / 9) : 0
}

const collectHlsDefinitions = (definitions) => {
  return (Array.isArray(definitions) ? definitions : [])
    .filter((item) => String(item?.format || '').toLowerCase() === 'hls')
    .filter((item) => safeUrl(item?.videoUrl))
    .sort((left, right) => {
      const heightDelta = parseQualityHeight(right) - parseQualityHeight(left)
      if (heightDelta !== 0) {
        return heightDelta
      }
      return parseQualityBandwidth(right) - parseQualityBandwidth(left)
    })
}

const estimateBandwidth = (definition) => {
  const explicit = parseQualityBandwidth(definition)
  if (explicit > 0) {
    return explicit
  }

  const height = parseQualityHeight(definition)
  if (height >= 1080) return 4_000_000
  if (height >= 720) return 2_500_000
  if (height >= 480) return 1_500_000
  if (height >= 360) return 900_000
  return 500_000
}

const buildHlsQualitiesFromDefinitions = (definitions) => {
  const qualities = []
  const seen = new Set()

  for (const item of collectHlsDefinitions(definitions)) {
    const videoUrl = safeUrl(item?.videoUrl)
    const height = parseQualityHeight(item) || null
    const width = height ? estimateWidth(item, height) : null
    const bandwidth = estimateBandwidth(item)
    const qualityId = `yp-hls:${width || 0}x${height || 0}:${bandwidth || 0}`
    if (!videoUrl || seen.has(qualityId)) {
      continue
    }
    seen.add(qualityId)
    qualities.push({
      id: qualityId,
      value: qualityId,
      label: height ? `${height}p` : qualityId,
      width,
      height,
      bandwidth,
      codec: null,
      src: videoUrl,
    })
  }

  qualities.sort((left, right) => {
    const heightDelta = (right.height || 0) - (left.height || 0)
    if (heightDelta !== 0) {
      return heightDelta
    }
    return (right.bandwidth || 0) - (left.bandwidth || 0)
  })
  return qualities
}

const mapPlaybackPayload = (targetUrl, definitions, { title, thumbnail, uploader_name, uploader_url } = {}) => {
  const basePayload = { title: title || null, thumbnail: thumbnail || null, uploader_name: uploader_name || null, uploader_url: uploader_url || null }
  const hlsDefinition = collectHlsDefinitions(definitions)[0]
  if (hlsDefinition?.videoUrl) {
    const qualities = buildHlsQualitiesFromDefinitions(definitions)
    return {
      ...basePayload,
      stream_type: 'hls',
      video_url: hlsDefinition.videoUrl,
      audio_url: null,
      mpd_url: null,
      mpd_content: null,
      qualities: qualities.length > 0 ? qualities : null,
      default_quality_id: qualities[0]?.id || null,
      supports_manual_quality: qualities.length > 1,
      metadata: {
        provider: 'youporn',
        url: targetUrl,
      },
    }
  }

  const mp4Definition = pickBestDefinition(definitions, 'mp4')
  if (mp4Definition?.videoUrl) {
    return {
      ...basePayload,
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
    const cached = await getCachedPayload(cacheKey)
    if (cached) {
      return cached
    }
  }

  const requestContext = buildRequestContext(normalizedUrl)
  const htmlText = await fetchPageHtml(normalizedUrl, {
    cookie: buildCookieHeader(cookie),
    referer: requestContext.referer,
    origin: requestContext.origin,
    userAgent: DEFAULT_USER_AGENT,
    fetchImpl,
  })
  const definitions = (await expandMediaDefinitions(extractMediaDefinitions(htmlText), cookie, requestContext, fetchImpl))
    .filter((item) => safeUrl(item?.videoUrl))
  const title = String(extractPageTitle(htmlText) || '').trim() || null
  const thumbnail = String(extractPageThumbnail(htmlText) || '').trim() || null
  const uploader_name = extractYpUploaderName(htmlText)
  const uploader_url = extractYpUploaderUrl(htmlText, normalizedUrl)
  const payload = mapPlaybackPayload(normalizedUrl, definitions, { title, thumbnail, uploader_name, uploader_url })
  setCachedPayload(cacheKey, payload)
  return payload
}
