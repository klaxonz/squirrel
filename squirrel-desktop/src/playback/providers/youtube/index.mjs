import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'

import { youtubeOAuthStateFilePath } from '../../../constants.mjs'
import { prewarmYoutubeiRuntime, resolveYoutubeiPayload } from './youtubei_core.mjs'
import { createPlaybackCache } from '../shared/playback-cache.mjs'

const RESOLVE_RETRY_DELAY_MS = 500
// Bump whenever the media authorization contract changes. Older IOS/no-pot
// manifests can start at byte zero but become permanently unusable after seek.
const PLAYBACK_CACHE_VERSION = 'mweb-pot-v1'
const cache = createPlaybackCache('youtube')
const playbackRefreshes = new Map()

const YOUTUBE_ID_PATTERNS = [
  /[?&]v=([\w-]{11})/i,
  /\/shorts\/([\w-]{11})/i,
  /youtu\.be\/([\w-]{11})/i,
  /\/embed\/([\w-]{11})/i,
]

const extractYouTubeVideoId = (targetUrl) => {
  const input = String(targetUrl || '').trim()
  if (!input) return ''

  for (const pattern of YOUTUBE_ID_PATTERNS) {
    const match = input.match(pattern)
    if (match?.[1]) {
      return match[1]
    }
  }

  return ''
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const cacheScopeForCookie = (cookie) => {
  const normalizedCookie = String(cookie || '').trim()
  if (!normalizedCookie) {
    return 'anon'
  }

  return `cookie:${createHash('sha1').update(normalizedCookie).digest('hex').slice(0, 16)}`
}

const resolveOAuthStateFilePath = () => {
  const fromEnv = String(process.env.YOUTUBE_OAUTH_STATE_FILE || '').trim()
  return fromEnv || youtubeOAuthStateFilePath || ''
}

const cacheScopeForOAuth = () => {
  const stateFile = resolveOAuthStateFilePath()
  if (!stateFile) {
    return 'oauth:none'
  }

  try {
    return `oauth:${createHash('sha1').update(readFileSync(stateFile)).digest('hex').slice(0, 16)}`
  } catch {
    console.debug('[squirrel-desktop] youtube/index: cacheScopeForOAuth read failed', stateFile)
    return 'oauth:none'
  }
}

const sortFormats = (formats) => {
  return [...formats].sort((left, right) => {
    const heightDelta = (right.height || 0) - (left.height || 0)
    if (heightDelta !== 0) return heightDelta
    return (right.bitrate || 0) - (left.bitrate || 0)
  })
}

const parseMimeParts = (mimeType) => {
  const [basePart, ...params] = String(mimeType || '').split(';')
  const mime = basePart.trim() || ''
  let codecs = ''
  for (const param of params) {
    const [key, rawValue] = param.split('=')
    if (String(key || '').trim().toLowerCase() === 'codecs') {
      codecs = String(rawValue || '').trim().replace(/^"|"$/g, '')
      break
    }
  }
  return { mime, codecs }
}

const normalizeCodecFamily = (codecString) => {
  const normalized = String(codecString || '').toLowerCase()
  if (!normalized) return null
  if (normalized.includes('av01') || normalized.includes('av1')) return 'av1'
  if (normalized.includes('vp09') || normalized.includes('vp9')) return 'vp9'
  if (normalized.includes('avc1') || normalized.includes('avc') || normalized.includes('h264')) return 'avc'
  if (normalized.includes('mp4a') || normalized.includes('aac')) return 'aac'
  if (normalized.includes('opus')) return 'opus'
  return normalized
}

const qualityBucketKey = (format, fallbackIndex) => {
  if (typeof format?.height === 'number' && format.height > 0) {
    return `height:${format.height}`
  }
  const label = String(format?.quality_label ?? format?.itag ?? fallbackIndex).trim().toLowerCase()
  return `label:${label}`
}

const pickFormats = (formats, predicate) => {
  return sortFormats((formats || []).filter((format) => predicate(format) && format?.url))
}

/**
 * Quality ladder for the player menu. Built from Innertube adaptive_formats
 * (official metadata) — not from homemade MPD parsing.
 */
const buildQualities = (formats, { requireUrl = true } = {}) => {
  const seen = new Set()
  const candidates = sortFormats((formats || []).filter((format) => {
    if (!format?.has_video) return false
    if (requireUrl && !format?.url) return false
    return true
  }))

  return candidates.reduce((qualities, format, index) => {
    const bucketKey = qualityBucketKey(format, index)
    if (seen.has(bucketKey)) {
      return qualities
    }
    seen.add(bucketKey)
    const { codecs } = parseMimeParts(format.mime_type)
    const id = String(format.itag ?? format.quality_label ?? index)
    qualities.push({
      id,
      value: id,
      label: format.quality_label || (format.height ? `${format.height}p` : id),
      height: typeof format.height === 'number' ? format.height : null,
      bandwidth: typeof format.bitrate === 'number' ? format.bitrate : null,
      codec: normalizeCodecFamily(codecs) || undefined,
      src: format.url || undefined,
    })
    return qualities
  }, [])
}

const pickQualitySourceFormats = (formats) => {
  const adaptiveVideo = (formats || []).filter((format) => format?.has_video && !format?.has_audio)
  if (adaptiveVideo.length > 0) {
    return adaptiveVideo
  }
  return (formats || []).filter((format) => format?.has_video)
}

/** Higher is better. Official youtubei.js toDash > YouTube-hosted MPD > progressive. */
const scoreMappedPayload = (payload) => {
  if (!payload) return 0
  const qualityCount = Array.isArray(payload.qualities) ? payload.qualities.length : 0
  if (payload.stream_type === 'dash' && payload.mpd_content) {
    // Official VideoInfo.toDash() body — preferred playback path (FreeTube data URL + shaka).
    return 2000 + qualityCount * 10
  }
  if (payload.stream_type === 'dash' && payload.mpd_url) {
    // Official streaming_data.dash_manifest_url from YouTube.
    return 1500 + qualityCount * 10
  }
  if (payload.stream_type === 'hls' && payload.video_url) {
    return 500 + qualityCount
  }
  if (payload.stream_type === 'progressive' && payload.video_url) {
    return 100 + qualityCount
  }
  return 0
}

/**
 * Official youtubei.js playback mapping (FreeTube-compatible, no homemade MPD):
 * 1. VideoInfo.toDash() → mpd_content  (primary — FreeTube data: URL + shaka)
 * 2. streaming_data.dash_manifest_url → mpd_url
 * 3. live HLS
 * 4. progressive muxed (last resort only)
 */
const mapPlaybackPayload = (response) => {
  const formats = Array.isArray(response?.formats) ? response.formats : []
  const bestProgressive = pickFormats(formats, (format) => format.has_audio && format.has_video)[0] || null
  const officialLocalDash = typeof response?.local_dash_manifest === 'string'
    ? response.local_dash_manifest.trim()
    : ''
  const dashManifestUrl = String(response?.streaming_data?.dash_manifest_url || '').trim()
  const hlsManifestUrl = String(response?.streaming_data?.hls_manifest_url || '').trim()
  const isLive = response?.basic_info?.is_live === true || response?.basic_info?.is_post_live_dvr === true
  const title = String(response?.basic_info?.title || '').trim() || null
  const thumbnails = response?.basic_info?.thumbnails
  const thumbnail = Array.isArray(thumbnails) ? thumbnails[thumbnails.length - 1]?.url || null : null
  const uploaderName = String(response?.basic_info?.uploader || response?.basic_info?.channel || '').trim() || null
  const uploaderUrl = String(response?.basic_info?.uploader_url || response?.basic_info?.channel_url || '').trim() || null
  const basePayload = { title, thumbnail, uploader_name: uploaderName, uploader_url: uploaderUrl }

  if (isLive && hlsManifestUrl) {
    return {
      ...basePayload,
      stream_type: 'hls',
      video_url: hlsManifestUrl,
      audio_url: null,
      mpd_url: null,
      mpd_content: null,
      qualities: null,
      default_quality_id: null,
      supports_manual_quality: false,
    }
  }

  // 1) Official youtubei.js DASH (VideoInfo.toDash) — FreeTube data: + shaka.
  if (officialLocalDash) {
    const qualities = buildQualities(pickQualitySourceFormats(formats), {
      // toDash already deciphered segment URLs inside the MPD; menu can list
      // adaptive rungs even when our parallel collectFormats missed a URL.
      requireUrl: false,
    })
    return {
      ...basePayload,
      stream_type: 'dash',
      video_url: null,
      audio_url: null,
      mpd_url: null,
      mpd_content: officialLocalDash,
      qualities: qualities.length > 0 ? qualities : null,
      default_quality_id: qualities[0]?.id || null,
      supports_manual_quality: qualities.length > 1,
    }
  }

  // 2) Official YouTube-hosted DASH manifest URL.
  if (dashManifestUrl) {
    const qualities = buildQualities(pickQualitySourceFormats(formats), { requireUrl: false })
    return {
      ...basePayload,
      stream_type: 'dash',
      video_url: null,
      audio_url: null,
      mpd_url: dashManifestUrl,
      mpd_content: null,
      qualities: qualities.length > 0 ? qualities : null,
      default_quality_id: qualities[0]?.id || null,
      supports_manual_quality: qualities.length > 1,
    }
  }

  // 3) Progressive muxed — last resort (typically itag 18 / 360p only).
  if (bestProgressive?.url) {
    const progressiveQualities = buildQualities([bestProgressive], { requireUrl: true })
    return {
      ...basePayload,
      stream_type: 'progressive',
      video_url: bestProgressive.url,
      audio_url: null,
      mpd_url: null,
      mpd_content: null,
      qualities: progressiveQualities.length > 0 ? progressiveQualities : null,
      default_quality_id: progressiveQualities[0]?.id || null,
      supports_manual_quality: progressiveQualities.length > 1,
    }
  }

  if (hlsManifestUrl) {
    return {
      ...basePayload,
      stream_type: 'hls',
      video_url: hlsManifestUrl,
      audio_url: null,
      mpd_url: null,
      mpd_content: null,
      qualities: null,
      default_quality_id: null,
      supports_manual_quality: false,
    }
  }

  throw new Error('Desktop YouTube provider did not return a playable manifest or stream')
}

export const clearYouTubePlaybackCache = () => {
  cache.clearCache()
}

export const resolveYouTubeOAuthSetup = () => {
  return resolveYoutubeiPayload({ action: 'oauth-setup' })
}

export const resolveYouTubeOAuthStatus = () => {
  return resolveYoutubeiPayload({ action: 'oauth-status' })
}

export const resolveYouTubeOAuthRevoke = () => {
  clearYouTubePlaybackCache()
  return resolveYoutubeiPayload({ action: 'oauth-revoke' })
}

export async function resolveYouTubeSubtitles(targetUrl, { cookie = '', lang = '', format = 'vtt' } = {}) {
  const videoId = extractYouTubeVideoId(targetUrl)
  if (!videoId) {
    throw new Error('Invalid YouTube URL')
  }

  const payload = await resolveYoutubeiPayload({
    action: 'captions',
    video_id: videoId,
    format,
    ...(lang ? { lang } : {}),
    ...(cookie ? { cookie } : {}),
  })
  if (payload?.status !== 'ok' || !payload?.content) {
    throw new Error('Desktop YouTube provider did not return subtitle content')
  }

  return {
    content: payload.content,
    format: payload.format || format,
    language_code: payload.language_code || null,
    language_name: payload.language_name || null,
    translated: payload.translated === true,
    kind: payload.kind || null,
  }
}

export const prewarmYouTubePlayback = (cookie = '') => {
  return prewarmYoutubeiRuntime(cookie)
}

const resolveFreshYouTubePlayback = async ({ videoId, cookie, cacheKey }) => {
  let bestPayload = null
  let lastError = null
  const maxAttempts = 2
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      const response = await resolveYoutubeiPayload({
        video_id: videoId,
        resolution_mode: 'all',
        ...(cookie ? { cookie } : {}),
      })
      if (response?.status === 'ok') {
        const mapped = mapPlaybackPayload(response)
        if (!bestPayload || scoreMappedPayload(mapped) > scoreMappedPayload(bestPayload)) {
          bestPayload = mapped
        }
        // Official toDash body is ideal — stop early.
        if (scoreMappedPayload(mapped) >= 2000) {
          lastError = null
          break
        }
        lastError = null
      } else {
        lastError = new Error(String(response?.error?.message || 'Desktop YouTube provider failed'))
      }
    } catch (error) {
      lastError = error
    }

    if (attempt + 1 < maxAttempts && scoreMappedPayload(bestPayload) < 2000) {
      await wait(RESOLVE_RETRY_DELAY_MS)
    }
  }

  if (bestPayload) {
    await cache.setCachedPayload(cacheKey, bestPayload)
    return bestPayload
  }

  if (lastError) {
    throw lastError
  }
  throw new Error('Desktop YouTube provider failed')
}

/** Deduplicate foreground resolves and stale-while-revalidate refreshes. */
const refreshYouTubePlayback = (params) => {
  const existing = playbackRefreshes.get(params.cacheKey)
  if (existing) return existing

  const refresh = resolveFreshYouTubePlayback(params)
    .finally(() => {
      if (playbackRefreshes.get(params.cacheKey) === refresh) {
        playbackRefreshes.delete(params.cacheKey)
      }
    })
  playbackRefreshes.set(params.cacheKey, refresh)
  return refresh
}

export async function resolveYouTubePlayback(targetUrl, { cookie = '', forceRefresh = false } = {}) {
  const videoId = extractYouTubeVideoId(targetUrl)
  if (!videoId) {
    throw new Error('Invalid YouTube URL')
  }

  const cacheKey = `${PLAYBACK_CACHE_VERSION}|${videoId}|${cacheScopeForCookie(cookie)}|${cacheScopeForOAuth()}`
  const params = { videoId, cookie, cacheKey }
  const cached = forceRefresh ? null : await cache.getCachedPayload(cacheKey)

  // A cache entry lives for only five minutes and is scoped by cookie/OAuth
  // identity + authorization contract version. An official toDash payload is
  // therefore safe to start immediately; refresh its signed URLs in the
  // background so the next navigation is equally fast. This removes the full
  // youtubei/PO-token round trip from repeat startup without extending URL TTL.
  if (cached && scoreMappedPayload(cached) >= 2000) {
    void refreshYouTubePlayback(params).catch((error) => {
      console.debug('[squirrel-desktop] youtube playback background refresh failed', error)
    })
    return cached
  }

  try {
    const fresh = await refreshYouTubePlayback(params)
    // Do not replace a still-valid adaptive source with a progressive collapse.
    return cached && scoreMappedPayload(cached) > scoreMappedPayload(fresh) ? cached : fresh
  } catch (error) {
    if (cached) return cached
    throw error
  }
}
