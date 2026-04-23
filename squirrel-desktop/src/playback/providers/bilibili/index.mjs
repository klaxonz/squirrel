import { createHash } from 'node:crypto'

const CACHE_TTL_MS = 5 * 60 * 1000
const playbackCache = new Map()
const wbiKeyCache = {
  value: null,
  expiresAt: 0,
}

const USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
const BILIBILI_REFERER = 'https://www.bilibili.com/'

const WBI_MIXIN_KEY_ENC_TAB = [
  46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
  33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
  61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
  36, 20, 34, 44, 52,
]

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

const escapeXml = (value) => {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;')
}

const normalizeTargetUrl = (targetUrl) => {
  const value = String(targetUrl || '').trim()
  if (!value) return ''

  try {
    return new URL(value).toString()
  } catch {
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
}

const buildHeaders = (cookie = '', extra = {}) => {
  const headers = {
    Accept: 'application/json',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    Referer: BILIBILI_REFERER,
    'User-Agent': USER_AGENT,
    ...extra,
  }

  if (cookie) {
    headers.Cookie = cookie
  }

  return headers
}

const fetchJson = async (url, { cookie = '', params = null, timeoutMs = 25000 } = {}) => {
  const target = new URL(url)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== null && value !== undefined && value !== '') {
        target.searchParams.set(key, String(value))
      }
    }
  }

  const abortController = new AbortController()
  const timer = setTimeout(() => abortController.abort(), timeoutMs)
  try {
    const response = await fetch(target, {
      headers: buildHeaders(cookie),
      signal: abortController.signal,
    })
    const payload = await response.json()

    if (!response.ok) {
      throw new Error(`Bilibili request failed with HTTP ${response.status}`)
    }

    const code = payload?.code
    if (code !== undefined && code !== 0) {
      throw new Error(`${payload?.message || payload?.msg || code} (code=${code})`)
    }

    return payload?.data || payload || {}
  } finally {
    clearTimeout(timer)
  }
}

const resolveRedirectUrl = async (targetUrl, cookie = '') => {
  let currentUrl = targetUrl
  for (let index = 0; index < 5; index += 1) {
    const response = await fetch(currentUrl, {
      headers: buildHeaders(cookie),
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

const extractPageIndex = (targetUrl) => {
  try {
    const url = new URL(targetUrl)
    const page = url.searchParams.get('p') || url.searchParams.get('page')
    const numericPage = Number.parseInt(page || '', 10)
    return Number.isFinite(numericPage) ? Math.max(numericPage - 1, 0) : 0
  } catch {
    return 0
  }
}

const extractVideoId = (targetUrl) => {
  const input = String(targetUrl || '')
  const bvidMatch = input.match(/(BV[0-9A-Za-z]{10,})/)
  if (bvidMatch?.[1]) {
    return { bvid: bvidMatch[1], aid: null }
  }

  const avMatch = input.match(/\/av(\d+)/i)
  if (avMatch?.[1]) {
    return { bvid: null, aid: Number.parseInt(avMatch[1], 10) }
  }

  try {
    const url = new URL(input)
    const queryBvid = url.searchParams.get('bvid')
    if (queryBvid && /^BV[0-9A-Za-z]{10,}$/.test(queryBvid)) {
      return { bvid: queryBvid, aid: null }
    }
    const queryAid = url.searchParams.get('aid') || url.searchParams.get('avid')
    const numericAid = Number.parseInt(queryAid || '', 10)
    if (Number.isFinite(numericAid)) {
      return { bvid: null, aid: numericAid }
    }
  } catch {
    // Ignore URL parse failures.
  }

  return { bvid: null, aid: null }
}

const getMixinKey = (value) => {
  return WBI_MIXIN_KEY_ENC_TAB
    .map((index) => value[index] || '')
    .join('')
    .slice(0, 32)
}

const getWbiKeys = async (cookie = '') => {
  if (wbiKeyCache.value && wbiKeyCache.expiresAt > Date.now()) {
    return wbiKeyCache.value
  }

  const nav = await fetchJson('https://api.bilibili.com/x/web-interface/nav', {
    cookie,
    timeoutMs: 15000,
  })
  const imgUrl = String(nav?.wbi_img?.img_url || '')
  const subUrl = String(nav?.wbi_img?.sub_url || '')
  const imgKey = imgUrl.split('/').pop()?.split('.')[0] || ''
  const subKey = subUrl.split('/').pop()?.split('.')[0] || ''

  if (!imgKey || !subKey) {
    throw new Error('Bilibili WBI keys are missing')
  }

  wbiKeyCache.value = { imgKey, subKey }
  wbiKeyCache.expiresAt = Date.now() + 60 * 60 * 1000
  return wbiKeyCache.value
}

const signWbiParams = async (params, cookie = '') => {
  const { imgKey, subKey } = await getWbiKeys(cookie)
  const mixinKey = getMixinKey(`${imgKey}${subKey}`)
  const cleanParams = {
    ...params,
    wts: String(Math.round(Date.now() / 1000)),
  }
  const sortedEntries = Object.entries(cleanParams)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => [
      key,
      String(value).replace(/[!'()*]/g, ''),
    ])
  const query = new URLSearchParams(sortedEntries).toString()
  const wRid = createHash('md5').update(`${query}${mixinKey}`).digest('hex')
  return {
    ...Object.fromEntries(sortedEntries),
    w_rid: wRid,
  }
}

const fetchVideoInfo = async (targetUrl, cookie = '') => {
  const normalizedUrl = await normalizeVideoUrl(targetUrl, cookie)
  const pageIndex = extractPageIndex(normalizedUrl)
  const { bvid, aid } = extractVideoId(normalizedUrl)

  if (!bvid && !aid) {
    throw new Error('URL is not a supported Bilibili video link')
  }

  const infoParams = {}
  if (bvid) {
    infoParams.bvid = bvid
  } else {
    infoParams.aid = String(aid)
  }

  const info = await fetchJson('https://api.bilibili.com/x/web-interface/view', {
    cookie,
    params: infoParams,
  })
  const pages = Array.isArray(info?.pages) ? info.pages : []
  const pageInfo = pages[Math.min(pageIndex, Math.max(pages.length - 1, 0))] || null
  const cid = Number.parseInt(String(pageInfo?.cid || ''), 10)

  if (!Number.isFinite(cid)) {
    throw new Error('Failed to resolve Bilibili cid')
  }

  return {
    info,
    context: {
      url: normalizedUrl,
      pageIndex,
      bvid: info?.bvid || bvid || null,
      aid: info?.aid || aid || null,
      cid,
    },
  }
}

const fetchPlayData = async (targetUrl, cookie = '') => {
  const { context } = await fetchVideoInfo(targetUrl, cookie)
  const params = {
    cid: String(context.cid),
    qn: '127',
    fnver: '0',
    fnval: '4048',
    fourk: '1',
  }

  if (context.bvid) {
    params.bvid = context.bvid
  } else if (context.aid) {
    params.aid = String(context.aid)
  }

  const signedParams = await signWbiParams(params, cookie)
  const playData = await fetchJson('https://api.bilibili.com/x/player/wbi/playurl', {
    cookie,
    params: signedParams,
  })

  return { playData, context }
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
      id: String(stream?.id ?? key),
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
    `id="${escapeXml(stream?.id ?? stream?.bandwidth ?? urls[0])}"`,
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

  const videoRepresentations = videoStreams
    .map((stream) => buildRepresentation(stream, 'video'))
    .filter(Boolean)
    .join('')
  const audioRepresentations = audioStreams
    .map((stream) => buildRepresentation(stream, 'audio'))
    .filter(Boolean)
    .join('')

  if (!videoRepresentations || !audioRepresentations) {
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
    `<AdaptationSet contentType="video" mimeType="video/mp4" segmentAlignment="true">${videoRepresentations}</AdaptationSet>`,
    `<AdaptationSet contentType="audio" mimeType="audio/mp4" segmentAlignment="true">${audioRepresentations}</AdaptationSet>`,
    '</Period>',
    '</MPD>',
  ].join('')
}

const mapPlaybackPayload = ({ playData, context }) => {
  const dashData = playData?.dash
  const localDashManifest = dashData ? buildLocalDashManifest(dashData) : null
  const qualities = buildQualities(dashData)

  if (localDashManifest) {
    return {
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

  throw new Error('Bilibili provider did not return a playable DASH payload')
}

export const clearBilibiliPlaybackCache = () => {
  playbackCache.clear()
}

export async function resolveBilibiliPlayback(targetUrl, { cookie = '', forceRefresh = false } = {}) {
  const normalizedUrl = await normalizeVideoUrl(targetUrl, cookie)
  const cacheKey = `${normalizedUrl}|cookie=${cookie ? '1' : '0'}`
  if (!forceRefresh) {
    const cached = getCachedPayload(cacheKey)
    if (cached) {
      return cached
    }
  }

  const response = await fetchPlayData(normalizedUrl, cookie)
  const payload = mapPlaybackPayload(response)
  setCachedPayload(cacheKey, payload)
  return payload
}
