import { getCachedPayload, normalizeTargetUrl, setCachedPayload } from '../shared/adult-page.mjs'

const MISSAV_ORIGIN = 'https://missav.ai'

const stripHtml = (value) => String(value || '').replace(/<[^>]*>/g, '').trim()

const stripHtmlWithSpaces = (value) => stripHtml(String(value || '').replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ')

const extractVideoNo = (text) => {
  const normalized = String(text || '').trim()
  const match = normalized.match(/\b([A-Za-z]{2,10}-\d{2,})\b/)
  if (match?.[1]) {
    return match[1].toUpperCase()
  }
  return normalized.split(/\s+/)[0]?.toUpperCase() || ''
}

const extractJavdbTitle = (htmlText) => {
  const titleBlocks = [...String(htmlText || '').matchAll(/<div[^>]+class=["'][^"']*\btitle\b[^"']*["'][^>]*>([\s\S]*?)<\/div>/gi)]
  for (const block of titleBlocks) {
    const strongParts = [...block[1].matchAll(/<strong[^>]*>([\s\S]*?)<\/strong>/gi)]
      .map((match) => stripHtml(match[1]))
      .filter(Boolean)
    if (strongParts.length > 0) {
      return strongParts.join(' ')
    }
  }

  const title = String(htmlText || '').match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1] || ''
  return stripHtml(title)
}

const extractJavdbDisplayTitle = (htmlText) => {
  const titleBlock = String(htmlText || '').match(/<div[^>]+class=["'][^"']*\btitle\b[^"']*["'][^>]*>([\s\S]*?)<\/div>/i)?.[1]
  return titleBlock ? stripHtmlWithSpaces(titleBlock) : ''
}

const extractJavdbImage = (htmlText, baseUrl) => {
  const imageMatch = String(htmlText || '').match(/<img\b(?=[^>]*class=["'][^"']*\bvideo-cover\b)[^>]*src=["']([^"']+)["']/i)
    || String(htmlText || '').match(/<img\b(?=[^>]*src=["']([^"']+)["'])(?=[^>]*class=["'][^"']*\bvideo-cover\b)[^>]*>/i)
  const src = imageMatch?.[1] || ''
  return src ? new URL(src, baseUrl).toString() : ''
}

const extractJavdbInfoPanelText = (htmlText, labelPattern) => {
  for (const panel of String(htmlText || '').matchAll(/<div[^>]+class=["'][^"']*\bpanel-block\b[^"']*["'][^>]*>([\s\S]*?)<\/div>/gi)) {
    const text = stripHtmlWithSpaces(panel[1])
    if (labelPattern.test(text)) return { html: panel[1], text }
  }
  return { html: '', text: '' }
}

const extractJavdbPublishDate = (htmlText) => {
  const { text } = extractJavdbInfoPanelText(htmlText, /Released Date:/i)
  return text.match(/\b\d{4}-\d{2}-\d{2}\b/)?.[0] || null
}

const extractJavdbDuration = (htmlText) => {
  const { text } = extractJavdbInfoPanelText(htmlText, /Duration:/i)
  const minutes = Number.parseInt(text.match(/Duration:\s*(\d+)/i)?.[1] || '', 10)
  return Number.isFinite(minutes) ? minutes * 60 : null
}

const extractJavdbActors = (htmlText) => {
  const actors = []
  const seen = new Set()
  const categoryPaths = new Set(['censored', 'uncensored', 'western'])
  for (const match of String(htmlText || '').matchAll(/<a\b[^>]*href=["']([^"']*\/actors\/[^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi)) {
    const url = new URL(match[1], 'https://javdb.com').toString()
    const actorId = url.split('/').filter(Boolean).pop() || ''
    if (!actorId || categoryPaths.has(actorId)) continue
    const name = stripHtmlWithSpaces(match[2])
    if (!name || seen.has(url)) continue
    seen.add(url)
    actors.push({
      id: actorId,
      type: 'ACTOR',
      name,
      url,
      avatar: '',
      is_nsfw: true,
    })
  }
  return actors
}

const extractJavdbMetadata = (htmlText, targetUrl) => ({
  title: extractJavdbDisplayTitle(htmlText),
  thumbnail: extractJavdbImage(htmlText, targetUrl),
  publish_date: extractJavdbPublishDate(htmlText),
  duration: extractJavdbDuration(htmlText),
  actors: extractJavdbActors(htmlText),
})

const looksLikeChallengePage = (htmlText) => {
  return /just a moment|cf_chl_|cf-turnstile|challenges\.cloudflare\.com/i.test(String(htmlText || '').toLowerCase())
}

const extractPartsFromHtml = (htmlText) => {
  for (const script of String(htmlText || '').matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)) {
    const scriptText = script[1] || ''
    if (!scriptText.includes('m3u8|')) continue

    const match = scriptText.match(/'([^']*m3u8\|[^']*)'/)
    if (match?.[1]) {
      return match[1]
    }
  }
  return ''
}

const extractMissavSearchLinks = (htmlText, baseUrl) => {
  const links = []
  for (const block of String(htmlText || '').matchAll(/<div[^>]+class=["'][^"']*\bthumbnail\b[^"']*["'][^>]*>([\s\S]*?)<\/div>/gi)) {
    const href = block[1].match(/<a\b[^>]*href=["']([^"']+)["']/i)?.[1]
    if (!href) continue
    const resolvedUrl = new URL(href, baseUrl).toString()
    if (!links.includes(resolvedUrl)) {
      links.push(resolvedUrl)
    }
  }
  return links
}

const formatStreamUrl = (parts) => {
  const urlPath = String(parts || '').split('m3u8|')[1]?.split('|playlist|source')[0] || ''
  const urlWords = urlPath.split('|')
  const videoIndex = urlWords.indexOf('video')
  if (videoIndex < 6) {
    throw new Error('MissAV stream metadata is invalid')
  }

  const protocol = urlWords[videoIndex - 1]
  const videoFormat = urlWords[videoIndex + 1]
  const m3u8UrlPath = urlWords.slice(0, 5).reverse().join('-')
  const baseUrlPath = urlWords.slice(5, videoIndex - 1).reverse().join('.')
  return `${protocol}://${baseUrlPath}/${m3u8UrlPath}/${videoFormat}/${urlWords[videoIndex]}.m3u8`
}

const loadMissavHtml = async (targetUrl, loadDocumentHtml) => {
  const htmlText = await loadDocumentHtml(targetUrl, {
    timeoutMs: 30000,
    challengeTimeoutMs: 90000,
  })
  if (looksLikeChallengePage(htmlText)) {
    throw new Error('MissAV challenge blocked playback lookup')
  }
  return htmlText
}

const resolveMissavDetailStream = (htmlText, detailUrl, videoNo) => {
  const parts = extractPartsFromHtml(htmlText)
  if (!parts) {
    throw new Error(`MissAV detail page is missing stream metadata for ${videoNo}`)
  }

  return {
    streamUrl: formatStreamUrl(parts),
    referer: detailUrl,
  }
}

const resolveMissavStream = async (videoNo, loadDocumentHtml) => {
  const directUrl = `${MISSAV_ORIGIN}/${videoNo.toLowerCase()}`
  const directHtml = await loadMissavHtml(directUrl, loadDocumentHtml)
  const directParts = extractPartsFromHtml(directHtml)
  if (directParts) {
    return {
      streamUrl: formatStreamUrl(directParts),
      referer: directUrl,
    }
  }

  const searchUrl = `${MISSAV_ORIGIN}/search/${videoNo}`
  const searchHtml = await loadMissavHtml(searchUrl, loadDocumentHtml)
  const links = extractMissavSearchLinks(searchHtml, searchUrl)
  if (links.length === 0) {
    throw new Error(`No MissAV search results found for ${videoNo}`)
  }

  for (const detailUrl of links) {
    const detailHtml = await loadMissavHtml(detailUrl, loadDocumentHtml)
    const parts = extractPartsFromHtml(detailHtml)
    if (parts) {
      return {
        streamUrl: formatStreamUrl(parts),
        referer: detailUrl,
      }
    }
  }

  throw new Error(`MissAV detail pages are missing stream metadata for ${videoNo}`)
}

const mapPlaybackPayload = ({ streamUrl, referer, videoNo, targetUrl }) => ({
  stream_type: 'hls',
  video_url: streamUrl,
  audio_url: null,
  mpd_url: null,
  mpd_content: null,
  qualities: null,
  default_quality_id: null,
  supports_manual_quality: false,
  metadata: {
    provider: 'javdb',
    video_no: videoNo,
    source_url: targetUrl,
    referer,
  },
})

export async function resolveJavdbPlayback(targetUrl, {
  forceRefresh = false,
  loadDocumentHtml,
  title: sourceTitle = '',
  videoNo: sourceVideoNo = '',
} = {}) {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl || !new URL(normalizedUrl).hostname.endsWith('javdb.com')) {
    throw new Error('Invalid JavDB URL')
  }
  if (typeof loadDocumentHtml !== 'function') {
    throw new Error('JavDB playback requires browser document loading')
  }

  const cacheKey = normalizedUrl
  if (!forceRefresh) {
    const cached = getCachedPayload(cacheKey)
    if (cached) {
      return cached
    }
  }

  let videoNo = extractVideoNo(sourceVideoNo || sourceTitle)
  if (!videoNo) {
    const javdbHtml = await loadDocumentHtml(normalizedUrl, {
      timeoutMs: 30000,
      challengeTimeoutMs: 90000,
    })
    const title = extractJavdbTitle(javdbHtml)
    videoNo = extractVideoNo(title)
  }
  if (!videoNo) {
    throw new Error('JavDB video number was not found')
  }

  const stream = await resolveMissavStream(videoNo, loadDocumentHtml)
  const payload = mapPlaybackPayload({
    ...stream,
    videoNo,
    targetUrl: normalizedUrl,
  })
  setCachedPayload(cacheKey, payload)
  return payload
}

export async function resolveJavdbMetadata(targetUrl, { loadDocumentHtml } = {}) {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl || !new URL(normalizedUrl).hostname.endsWith('javdb.com')) {
    throw new Error('Invalid JavDB URL')
  }
  if (typeof loadDocumentHtml !== 'function') {
    throw new Error('JavDB metadata requires browser document loading')
  }

  const javdbHtml = await loadDocumentHtml(normalizedUrl, {
    timeoutMs: 30000,
    challengeTimeoutMs: 90000,
  })
  return extractJavdbMetadata(javdbHtml, normalizedUrl)
}

export const __testing = {
  extractVideoNo,
  extractJavdbTitle,
  extractJavdbMetadata,
  extractPartsFromHtml,
  extractMissavSearchLinks,
  formatStreamUrl,
}
