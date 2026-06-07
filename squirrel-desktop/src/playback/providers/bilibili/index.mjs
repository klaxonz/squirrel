import { createHash } from 'node:crypto'

import { CACHE_TTL_MS } from '../../../constants.mjs'
import { resolveBilibiliApiPayload, fetchBrowserJson, extractVideoId } from './request-runtime.mjs'
import { loadFileCache, saveFileCache } from '../../file-cache.mjs'
import { escapeXml } from '../shared/escape-xml.mjs'
const playbackCache = new Map()

const QUALITY_HEIGHT_MAP = new Map([
  [16, 360],
  [32, 480],
  [48, 400],
  [64, 720],
  [74, 720],
  [80, 1080],
  [112, 1080],
  [116, 1080],
  [120, 2160],
  [125, 2160],
  [126, 2160],
  [127, 4320],
])

const normalizeTargetUrl = (targetUrl) => {
  const value = String(targetUrl || '').trim()
  if (!value) return ''

  try {
    return new URL(value).toString()
  } catch (err) {
    console.debug('[squirrel-desktop] bilibili normalizeTargetUrl error', err)
    return ''
  }
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
  saveFileCache(cacheKey, value, CACHE_TTL_MS).catch((err) => {
    console.debug('[squirrel-desktop] bilibili cache save error', err)
  })
}

const cacheScopeForCookie = (cookie) => {
  const normalizedCookie = String(cookie || '').trim()
  if (!normalizedCookie) {
    return 'anonymous'
  }

  return `cookie:${createHash('sha1').update(normalizedCookie).digest('hex').slice(0, 16)}`
}

const resolveRedirectUrl = async (targetUrl, cookie = '') => {
  let currentUrl = targetUrl
  for (let index = 0; index < 5; index += 1) {
    const response = await fetch(currentUrl, {
      headers: cookie ? { cookie } : {},
      redirect: 'manual',
    })
    const location = response.headers.get('location')
    if (!location || response.status < 300 || response.status >= 400) {
      return currentUrl
    }
    currentUrl = new URL(location, currentUrl).toString()
  }
  return currentUrl
}

const normalizeVideoUrl = async (targetUrl, cookie = '') => {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    throw new Error('Invalid Bilibili URL')
  }

  const hostname = new URL(normalizedUrl).hostname.toLowerCase()
  if (hostname.endsWith('b23.tv')) {
    return resolveRedirectUrl(normalizedUrl, cookie)
  }
  return normalizedUrl
}

const fetchPlayData = async (targetUrl, { cookie = '', fetchImpl = null } = {}) => {
  return resolveBilibiliApiPayload(targetUrl, { cookie, fetchImpl })
}

const baseUrlOf = (stream) => {
  return stream?.baseUrl || stream?.base_url || ''
}

const backupUrlsOf = (stream) => {
  const urls = stream?.backupUrl || stream?.backup_url || []
  return Array.isArray(urls) ? urls.filter(Boolean).map(String) : []
}

const safeInt = (value) => {
  const numeric = Number.parseInt(String(value ?? ''), 10)
  return Number.isFinite(numeric) ? numeric : 0
}

const codecFamilyFromStream = (stream) => {
  const codecs = String(stream?.codecs || '').toLowerCase()
  if (codecs.includes('avc1') || codecs.includes('avc') || codecs.includes('h264')) return 'avc'
  if (codecs.includes('hev1') || codecs.includes('hvc1') || codecs.includes('hevc') || codecs.includes('h265')) return 'hevc'
  if (codecs.includes('av01') || codecs.includes('av1')) return 'av1'
  if (codecs.includes('vp09') || codecs.includes('vp9')) return 'vp9'

  const codecid = safeInt(stream?.codecid)
  if (codecid === 7) return 'avc'
  if (codecid === 12) return 'hevc'
  if (codecid === 13) return 'av1'
  return undefined
}

const representationIdForStream = (stream, kind) => {
  const codec = codecFamilyFromStream(stream)
    || (kind === 'audio' ? 'audio' : 'video')
  const rawId = stream?.id ?? stream?.bandwidth ?? kind
  const bandwidth = safeInt(stream?.bandwidth)
  const height = kind === 'video' ? safeInt(stream?.height) : 0
  return [kind, codec, rawId, height || null, bandwidth || null]
    .filter((part) => part !== null && part !== undefined && part !== '')
    .join('-')
}

const videoStreamSortKey = (stream) => {
  return [safeInt(stream?.height), safeInt(stream?.bandwidth)]
}

const sortVideoStreams = (streams) => {
  return [...streams].sort((left, right) => {
    const [leftHeight, leftBandwidth] = videoStreamSortKey(left)
    const [rightHeight, rightBandwidth] = videoStreamSortKey(right)
    if (rightHeight !== leftHeight) return rightHeight - leftHeight
    return rightBandwidth - leftBandwidth
  })
}

const groupVideoStreamsByCodec = (streams) => {
  const groups = new Map()
  for (const stream of streams) {
    const codec = codecFamilyFromStream(stream) || 'unknown'
    if (!groups.has(codec)) {
      groups.set(codec, [])
    }
    groups.get(codec).push(stream)
  }

  const codecPriority = new Map([
    ['avc', 0],
    ['vp9', 1],
    ['av1', 2],
    ['hevc', 3],
    ['unknown', 4],
  ])

  return Array.from(groups.entries())
    .map(([codec, codecStreams]) => [codec, sortVideoStreams(codecStreams)])
    .sort(([leftCodec, leftStreams], [rightCodec, rightStreams]) => {
      const leftPriority = codecPriority.get(leftCodec) ?? codecPriority.get('unknown')
      const rightPriority = codecPriority.get(rightCodec) ?? codecPriority.get('unknown')
      if (leftPriority !== rightPriority) return leftPriority - rightPriority
      const [leftHeight, leftBandwidth] = videoStreamSortKey(leftStreams[0] || {})
      const [rightHeight, rightBandwidth] = videoStreamSortKey(rightStreams[0] || {})
      if (rightHeight !== leftHeight) return rightHeight - leftHeight
      return rightBandwidth - leftBandwidth
    })
}

const buildQualities = (dashData) => {
  const videoStreams = sortVideoStreams(Array.isArray(dashData?.video) ? dashData.video : [])
  const seen = new Set()
  const qualities = []

  for (const stream of videoStreams) {
    const qn = safeInt(stream?.id)
    const height = QUALITY_HEIGHT_MAP.get(qn) || safeInt(stream?.height) || null
    const bandwidth = safeInt(stream?.bandwidth) || null
    const codec = codecFamilyFromStream(stream)
    const key = `${codec || ''}|${height || ''}|${bandwidth || ''}`
    if (seen.has(key)) continue
    seen.add(key)

    const label = height
      ? `${height}p${codec ? ` ${codec.toUpperCase()}` : ''}`
      : (bandwidth ? `${Math.round(bandwidth / 1000)}kbps` : 'unknown')
    qualities.push({
      id: representationIdForStream(stream, 'video'),
      value: label,
      label,
      height,
      bandwidth,
      codec,
    })
  }

  return qualities
}

const appendSegmentBase = (stream) => {
  const segmentBase = stream?.SegmentBase || stream?.segment_base || null
  if (!segmentBase || typeof segmentBase !== 'object') {
    return ''
  }

  const indexRange = segmentBase.indexRange || segmentBase.index_range
  const initRange = segmentBase.Initialization || segmentBase.initialization
  const attributes = indexRange ? ` indexRange="${escapeXml(indexRange)}"` : ''
  const initNode = initRange ? `<Initialization range="${escapeXml(initRange)}" />` : ''
  return `<SegmentBase${attributes}>${initNode}</SegmentBase>`
}

const buildRepresentation = (stream, kind) => {
  const urls = [baseUrlOf(stream), ...backupUrlsOf(stream)].filter(Boolean)
  if (urls.length === 0) {
    return ''
  }

  const mimeType = stream?.mimeType || stream?.mime_type || (kind === 'audio' ? 'audio/mp4' : 'video/mp4')
  const attributes = [
    `id="${escapeXml(representationIdForStream(stream, kind))}"`,
    `mimeType="${escapeXml(mimeType)}"`,
    stream?.codecs ? `codecs="${escapeXml(stream.codecs)}"` : '',
    stream?.bandwidth ? `bandwidth="${escapeXml(stream.bandwidth)}"` : '',
    kind === 'video' && stream?.width ? `width="${escapeXml(stream.width)}"` : '',
    kind === 'video' && stream?.height ? `height="${escapeXml(stream.height)}"` : '',
    kind === 'video' && stream?.frameRate ? `frameRate="${escapeXml(stream.frameRate)}"` : '',
  ].filter(Boolean)
  const baseUrls = urls.map((url) => `<BaseURL>${escapeXml(url)}</BaseURL>`).join('')
  return `<Representation ${attributes.join(' ')}>${baseUrls}${appendSegmentBase(stream)}</Representation>`
}

const buildLocalDashManifest = (dashData) => {
  const videoStreams = sortVideoStreams(Array.isArray(dashData?.video) ? dashData.video : [])
  const audioStreams = [...(Array.isArray(dashData?.audio) ? dashData.audio : [])]
    .sort((left, right) => safeInt(right?.bandwidth) - safeInt(left?.bandwidth))

  const videoAdaptationSets = groupVideoStreamsByCodec(videoStreams)
    .map(([, codecStreams]) => {
      const videoRepresentations = codecStreams
        .map((stream) => buildRepresentation(stream, 'video'))
        .filter(Boolean)
        .join('')

      if (!videoRepresentations) {
        return ''
      }

      return `<AdaptationSet contentType="video" mimeType="video/mp4" segmentAlignment="true">${videoRepresentations}</AdaptationSet>`
    })
    .filter(Boolean)
    .join('')
  const audioRepresentations = audioStreams
    .map((stream) => buildRepresentation(stream, 'audio'))
    .filter(Boolean)
    .join('')

  if (!videoAdaptationSets || !audioRepresentations) {
    return null
  }

  const attributes = [
    'xmlns="urn:mpeg:dash:schema:mpd:2011"',
    'type="static"',
    'profiles="urn:mpeg:dash:profile:isoff-on-demand:2011"',
    dashData?.duration ? `mediaPresentationDuration="PT${escapeXml(dashData.duration)}S"` : '',
    dashData?.minBufferTime ? `minBufferTime="PT${escapeXml(dashData.minBufferTime)}S"` : 'minBufferTime="PT1.5S"',
  ].filter(Boolean)

  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    `<MPD ${attributes.join(' ')}>`,
    '<Period start="PT0S">',
    videoAdaptationSets,
    `<AdaptationSet contentType="audio" mimeType="audio/mp4" segmentAlignment="true">${audioRepresentations}</AdaptationSet>`,
    '</Period>',
    '</MPD>',
  ].join('')
}

const summarizeUnplayablePayload = (playData) => {
  const dashVideoCount = Array.isArray(playData?.dash?.video) ? playData.dash.video.length : 0
  const dashAudioCount = Array.isArray(playData?.dash?.audio) ? playData.dash.audio.length : 0
  const durlCount = Array.isArray(playData?.durl) ? playData.durl.length : 0
  const supportFormats = Array.isArray(playData?.support_formats)
    ? playData.support_formats.map((item) => item?.new_description || item?.display_desc || item?.quality).filter(Boolean).slice(0, 5)
    : []

  return [
    `quality=${playData?.quality ?? 'unknown'}`,
    `dashVideo=${dashVideoCount}`,
    `dashAudio=${dashAudioCount}`,
    `durl=${durlCount}`,
    supportFormats.length ? `formats=${supportFormats.join(', ')}` : null,
    playData?.message ? `message=${playData.message}` : null,
  ].filter(Boolean).join('; ')
}

const mapPlaybackPayload = ({ playData, context, info }) => {
  const dashData = playData?.dash
  const localDashManifest = dashData ? buildLocalDashManifest(dashData) : null
  const qualities = buildQualities(dashData)
  const title = String(info?.data?.title || info?.title || '').trim() || null
  const thumbnail = String(info?.data?.pic || info?.pic || '').trim() || null
  const owner = info?.owner || info?.data?.owner || {}
  const uploaderName = String(owner?.name || '').trim() || null
  const uploaderAvatar = String(owner?.face || '').trim() || null
  const uploaderId = String(owner?.mid || '').trim() || null
  const uploaderUrl = uploaderId ? `https://space.bilibili.com/${uploaderId}` : null
  const basePayload = { title, thumbnail, uploader_name: uploaderName, uploader_url: uploaderUrl, uploader_avatar: uploaderAvatar }

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
      metadata: {
        bvid: context.bvid,
        aid: context.aid,
        cid: context.cid,
      },
    }
  }

  throw new Error(`Bilibili provider did not return a playable payload: ${summarizeUnplayablePayload(playData)}`)
}

function convertBilibiliSubtitleToSrt(body) {
  if (!Array.isArray(body)) return ''

  return body
    .map((item, index) => {
      const from = formatBilibiliSubtitleTime(item.from)
      const to = formatBilibiliSubtitleTime(item.to)
      const content = (item.content || '').trim()
      if (!content) return ''
      return `${index + 1}\n${from} --> ${to}\n${content}\n`
    })
    .filter(Boolean)
    .join('\n')
}

function formatBilibiliSubtitleTime(seconds) {
  const totalMs = Math.round(Number(seconds || 0) * 1000)
  const hrs = Math.floor(totalMs / 3600000)
  const mins = Math.floor((totalMs % 3600000) / 60000)
  const secs = Math.floor((totalMs % 60000) / 1000)
  const ms = totalMs % 1000
  return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')},${String(ms).padStart(3, '0')}`
}

export async function resolveBilibiliSubtitles(targetUrl, { cookie = '', lang = '', format = 'srt' } = {}) {
  const { bvid, aid } = extractVideoId(targetUrl)
  if (!bvid && !aid) {
    throw new Error('Invalid Bilibili URL')
  }

  const infoParams = bvid ? { bvid } : { aid: String(aid) }
  const info = await fetchBrowserJson('https://api.bilibili.com/x/web-interface/view', {
    cookie,
    params: infoParams,
  })

  const subtitleList = Array.isArray(info?.subtitle?.list) ? info.subtitle.list : []
  if (!subtitleList.length) {
    throw new Error('No subtitles available')
  }

  let subtitle = lang
    ? subtitleList.find((s) => s.lan === lang)
    : null
  if (!subtitle) {
    subtitle = subtitleList[0]
  }

  const subtitleUrl = subtitle.subtitle_url
    ? (subtitle.subtitle_url.startsWith('//') ? `https:${subtitle.subtitle_url}` : subtitle.subtitle_url)
    : null
  if (!subtitleUrl) {
    throw new Error('Subtitle URL not found')
  }

  const response = await fetch(subtitleUrl, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      Referer: 'https://www.bilibili.com/',
    },
  })
  const subtitleData = await response.json()
  const body = Array.isArray(subtitleData?.body) ? subtitleData.body : []

  const srtContent = convertBilibiliSubtitleToSrt(body)
  if (!srtContent.trim()) {
    throw new Error('Subtitle content is empty')
  }

  return {
    content: srtContent,
    format,
    language_code: subtitle.lan,
    language_name: subtitle.lan_doc,
  }
}

export const clearBilibiliPlaybackCache = () => {
  playbackCache.clear()
}

export async function resolveBilibiliPlayback(targetUrl, { cookie = '', forceRefresh = false, fetchImpl = null } = {}) {
  const normalizedUrl = await normalizeVideoUrl(targetUrl, cookie)
  const cacheKey = `${normalizedUrl}|${cacheScopeForCookie(cookie)}`
  if (!forceRefresh) {
    const cached = getCachedPayload(cacheKey)
    if (cached) {
      return cached
    }
  }

  const response = await fetchPlayData(normalizedUrl, { cookie, fetchImpl })
  const payload = mapPlaybackPayload(response)
  setCachedPayload(cacheKey, payload)
  return payload
}
