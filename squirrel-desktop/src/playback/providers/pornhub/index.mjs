import { createHash } from 'node:crypto'

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

const extractUploaderName = (htmlText) => {
  const jsonLdScripts = htmlText.match(/<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi) || []
  for (const script of jsonLdScripts) {
    const authorMatch = script.match(/"author"\s*:\s*"([^"]+)"/i)
    if (authorMatch?.[1] && authorMatch[1].trim()) return authorMatch[1].trim()
  }
  return null
}

const extractUploaderUrl = (htmlText) => {
  const match = htmlText.match(/<a\b[^>]*href=["']((?:\/model\/|\/pornstar\/|\/channels\/)[^"']+)["'][^>]*>/i)
  if (match?.[1]) return new URL(match[1], 'https://www.pornhub.com').toString()
  return null
}

const buildCookieHeader = (cookie) => {
  return mergeCookieHeaders(AGE_GATE_COOKIE_HEADER, cookie)
}

const cacheScopeForCookie = (cookie) => {
  const normalizedCookie = String(cookie || '').trim()
  if (!normalizedCookie) {
    return 'anonymous'
  }

  return `cookie:${createHash('sha1').update(normalizedCookie).digest('hex').slice(0, 16)}`
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

const mapPlaybackPayload = (targetUrl, definitions, { title, thumbnail, uploader_name, uploader_url } = {}) => {
  const basePayload = { title: title || null, thumbnail: thumbnail || null, uploader_name: uploader_name || null, uploader_url: uploader_url || null }
  const hlsDefinition = pickBestDefinition(definitions, 'hls')
  if (hlsDefinition?.videoUrl) {
    const qualities = buildHlsQualities(definitions, 'ph-hls')
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
        provider: 'pornhub',
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

  const cacheKey = `${normalizedUrl}|${cacheScopeForCookie(cookie)}`
  if (!forceRefresh) {
    const cached = await getCachedPayload(cacheKey)
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
  const title = String(extractPageTitle(htmlText) || '').trim() || null
  const thumbnail = String(extractPageThumbnail(htmlText) || '').trim() || null
  const uploader_name = extractUploaderName(htmlText)
  const uploader_url = extractUploaderUrl(htmlText)
  const payload = mapPlaybackPayload(normalizedUrl, definitions, { title, thumbnail, uploader_name, uploader_url })
  setCachedPayload(cacheKey, payload)
  return payload
}
