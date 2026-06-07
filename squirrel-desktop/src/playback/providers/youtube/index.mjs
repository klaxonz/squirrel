import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'

import { prewarmYoutubeiRuntime, resolveYoutubeiPayload } from './youtubei_core.mjs'
import { loadFileCache, saveFileCache } from '../../file-cache.mjs'
import { escapeXml } from '../shared/escape-xml.mjs'

const CACHE_TTL_MS = 5 * 60 * 1000
const RESOLVE_RETRY_DELAY_MS = 500
const playbackCache = new Map()

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

const isExpired = (entry) => {
  return !entry || entry.expiresAt <= Date.now()
}

const getCachedPayload = (cacheKey) => {
  const cached = playbackCache.get(cacheKey)
  if (isExpired(cached)) {
    playbackCache.delete(cacheKey)
    return null
  }
  return cached.value
}

const setCachedPayload = (cacheKey, value) => {
  playbackCache.set(cacheKey, {
    value,
    expiresAt: Date.now() + CACHE_TTL_MS,
  })
  saveFileCache(cacheKey, value, CACHE_TTL_MS).catch(() => {})
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const cacheScopeForCookie = (cookie) => {
  const normalizedCookie = String(cookie || '').trim()
  if (!normalizedCookie) {
    return 'anon'
  }

  return `cookie:${createHash('sha1').update(normalizedCookie).digest('hex').slice(0, 16)}`
}

const cacheScopeForOAuth = () => {
  const stateFile = String(process.env.YOUTUBE_OAUTH_STATE_FILE || '').trim()
  if (!stateFile) {
    return 'oauth:none'
  }

  try {
    return `oauth:${createHash('sha1').update(readFileSync(stateFile)).digest('hex').slice(0, 16)}`
  } catch {
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

const representationGroupKey = (format, kind) => {
  const { mime, codecs } = parseMimeParts(format?.mime_type)
  return [kind, mime || '', codecs || ''].join('|')
}

const buildSegmentBaseXml = (format) => {
  const serializeRange = (range) => {
    if (!range) return ''
    if (typeof range === 'string') return range.trim()
    const start = range.start ?? range.begin ?? range.startMs
    const end = range.end ?? range.finish ?? range.endMs
    if (start === undefined || end === undefined) return ''
    return `${start}-${end}`
  }

  const indexRange = serializeRange(format.index_range)
  const initRange = serializeRange(format.init_range)
  const attributes = []
  if (indexRange) {
    attributes.push(`indexRange="${escapeXml(indexRange)}"`)
  }
  if (attributes.length === 0 && !initRange) {
    return ''
  }

  const initialization = initRange
    ? `<Initialization range="${escapeXml(initRange)}" />`
    : ''

  return `<SegmentBase${attributes.length > 0 ? ` ${attributes.join(' ')}` : ''}>${initialization}</SegmentBase>`
}

const buildRepresentationXml = (format, kind) => {
  const { mime, codecs } = parseMimeParts(format.mime_type)
  if (!mime || !format.url) {
    return ''
  }

  const attributes = [
    `id="${escapeXml(format.itag ?? format.quality_label ?? format.url)}"`,
    format.bitrate ? `bandwidth="${escapeXml(format.bitrate)}"` : '',
    `mimeType="${escapeXml(mime)}"`,
    codecs ? `codecs="${escapeXml(codecs)}"` : '',
    kind === 'video' && format.width ? `width="${escapeXml(format.width)}"` : '',
    kind === 'video' && format.height ? `height="${escapeXml(format.height)}"` : '',
    kind === 'audio' && format.audio_sample_rate ? `audioSamplingRate="${escapeXml(format.audio_sample_rate)}"` : '',
  ].filter(Boolean)

  const audioChannelNode = kind === 'audio' && format.audio_channels
    ? `<AudioChannelConfiguration schemeIdUri="urn:mpeg:dash:23003:3:audio_channel_configuration:2011" value="${escapeXml(format.audio_channels)}" />`
    : ''
  const labelNode = kind === 'audio' && format.language
    ? `<Label>${escapeXml(format.language)}</Label>`
    : ''

  return `<Representation ${attributes.join(' ')}><BaseURL>${escapeXml(format.url)}</BaseURL>${buildSegmentBaseXml(format)}${audioChannelNode}${labelNode}</Representation>`
}

const getFormatDurationSeconds = (format) => {
  try {
    const duration = Number(new URL(format?.url || '').searchParams.get('dur'))
    return Number.isFinite(duration) && duration > 0 ? duration : null
  } catch {
    return null
  }
}

const formatIsoDuration = (seconds) => {
  const duration = Number(seconds)
  if (!Number.isFinite(duration) || duration <= 0) {
    return ''
  }

  return `PT${Number(duration.toFixed(3))}S`
}

const buildFallbackLocalDashManifest = (formats) => {
  const videoFormats = sortFormats(
    (formats || []).filter((format) => format?.has_video && !format?.has_audio && format?.url)
  )
  const audioFormats = sortFormats(
    (formats || []).filter((format) => format?.has_audio && !format?.has_video && format?.url)
  )

  if (videoFormats.length === 0 || audioFormats.length === 0) {
    return null
  }

  const groupFormats = (items, kind) => {
    const grouped = new Map()
    for (const item of items) {
      const key = representationGroupKey(item, kind)
      if (!grouped.has(key)) {
        grouped.set(key, [])
      }
      grouped.get(key).push(item)
    }
    return Array.from(grouped.values())
  }

  const videoAdaptationSets = groupFormats(videoFormats, 'video')
    .map((group) => {
      const first = group[0]
      const { mime, codecs } = parseMimeParts(first?.mime_type)
      const videoRepresentations = group
        .map((format) => buildRepresentationXml(format, 'video'))
        .filter(Boolean)
        .join('')
      if (!videoRepresentations) {
        return ''
      }
      const attributes = [
        'contentType="video"',
        'segmentAlignment="true"',
        mime ? `mimeType="${escapeXml(mime)}"` : '',
        codecs ? `codecs="${escapeXml(codecs)}"` : '',
      ].filter(Boolean)
      return `<AdaptationSet ${attributes.join(' ')}>${videoRepresentations}</AdaptationSet>`
    })
    .filter(Boolean)
    .join('')
  const audioAdaptationSets = groupFormats(audioFormats, 'audio')
    .map((group) => {
      const first = group[0]
      const { mime, codecs } = parseMimeParts(first?.mime_type)
      const audioRepresentations = group
        .map((format) => buildRepresentationXml(format, 'audio'))
        .filter(Boolean)
        .join('')
      if (!audioRepresentations) {
        return ''
      }
      const attributes = [
        'contentType="audio"',
        'segmentAlignment="true"',
        mime ? `mimeType="${escapeXml(mime)}"` : '',
        codecs ? `codecs="${escapeXml(codecs)}"` : '',
      ].filter(Boolean)
      return `<AdaptationSet ${attributes.join(' ')}>${audioRepresentations}</AdaptationSet>`
    })
    .filter(Boolean)
    .join('')

  if (!videoAdaptationSets || !audioAdaptationSets) {
    return null
  }

  const mediaPresentationDuration = formatIsoDuration(
    Math.max(
      ...[...videoFormats, ...audioFormats]
        .map(getFormatDurationSeconds)
        .filter((duration) => typeof duration === 'number')
    )
  )
  const durationAttribute = mediaPresentationDuration
    ? ` mediaPresentationDuration="${escapeXml(mediaPresentationDuration)}"`
    : ''

  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    `<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011" minBufferTime="PT4S"${durationAttribute}>`,
    '<Period start="PT0S">',
    videoAdaptationSets,
    audioAdaptationSets,
    '</Period>',
    '</MPD>',
  ].join('')
}

const pickFormats = (formats, predicate) => {
  return sortFormats((formats || []).filter((format) => predicate(format) && format?.url))
}

const buildQualities = (formats) => {
  const seen = new Set()
  const candidates = sortFormats((formats || []).filter((format) => format?.has_video))

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
    })
    return qualities
  }, [])
}

const mapPlaybackPayload = (response) => {
  const formats = Array.isArray(response?.formats) ? response.formats : []
  const qualities = buildQualities(formats)
  const bestProgressive = pickFormats(formats, (format) => format.has_audio && format.has_video)[0] || null
  const hasAdaptiveSet =
    formats.some((format) => format?.has_video && !format?.has_audio && format?.url) &&
    formats.some((format) => format?.has_audio && !format?.has_video && format?.url)

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
      qualities: null,
      default_quality_id: null,
      supports_manual_quality: false,
    }
  }

  if (hasAdaptiveSet) {
    const localDashManifest = response?.local_dash_manifest || buildFallbackLocalDashManifest(formats)
    if (localDashManifest) {
      return {
        ...basePayload,
        stream_type: 'dash',
        video_url: null,
        audio_url: null,
        mpd_url: null,
        mpd_content: localDashManifest,
        qualities: qualities.length > 0 ? qualities : null,
        default_quality_id: qualities[0]?.id || null,
        supports_manual_quality: qualities.length > 1,
      }
    }
  }

  if (hasAdaptiveSet && dashManifestUrl) {
    return {
      ...basePayload,
      stream_type: 'dash',
      video_url: null,
      audio_url: null,
      mpd_url: dashManifestUrl,
      qualities: qualities.length > 0 ? qualities : null,
      default_quality_id: qualities[0]?.id || null,
      supports_manual_quality: qualities.length > 1,
    }
  }

  if (bestProgressive?.url) {
    return {
      ...basePayload,
      stream_type: 'progressive',
      video_url: bestProgressive.url,
      audio_url: null,
      mpd_url: null,
      mpd_content: null,
      qualities: qualities.length > 0 ? qualities : null,
      default_quality_id: qualities[0]?.id || null,
      supports_manual_quality: qualities.length > 1,
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
  playbackCache.clear()
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

export async function resolveYouTubePlayback(targetUrl, { cookie = '', forceRefresh = false } = {}) {
  const videoId = extractYouTubeVideoId(targetUrl)
  if (!videoId) {
    throw new Error('Invalid YouTube URL')
  }

  const cacheKey = `${videoId}|${cacheScopeForCookie(cookie)}|${cacheScopeForOAuth()}`
  const cached = getCachedPayload(cacheKey)
  if (!forceRefresh) {
    if (cached) {
      return cached
    }
  }

  let response
  let lastError = null
  const maxAttempts = cached ? 1 : 2
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      response = await resolveYoutubeiPayload({
        video_id: videoId,
        resolution_mode: 'all',
        ...(cookie ? { cookie } : {}),
      })
      if (response?.status === 'ok') {
        break
      }
      lastError = null
    } catch (error) {
      lastError = error
    }

    if (attempt + 1 < maxAttempts) {
      await wait(RESOLVE_RETRY_DELAY_MS)
    }
  }

  if (lastError && !response) {
    if (!forceRefresh && cached) {
      return cached
    }
    throw lastError
  }

  if (!response || response.status !== 'ok') {
    if (!forceRefresh && cached) {
      return cached
    }
    const errorMessage = response?.error?.message || 'Desktop YouTube provider failed'
    throw new Error(String(errorMessage))
  }

  const payload = mapPlaybackPayload(response)
  setCachedPayload(cacheKey, payload)
  return payload
}
