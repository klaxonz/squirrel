import {
  clampLimit,
  clampPage,
  fetchText,
  findBalancedJson,
  normalizeUrl,
  normalizeQuery,
  parseDuration,
  pickText,
  pickThumbnail,
  uniqueByUrl,
} from './shared.mjs'

const SITE = 'youtube'
const ORIGIN = 'https://www.youtube.com'
const DESKTOP_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'

const collectVideoRenderers = (node, output) => {
  if (!node || typeof node !== 'object') return
  if (node.videoRenderer) {
    output.push(node.videoRenderer)
    return
  }
  if (Array.isArray(node)) {
    node.forEach((item) => collectVideoRenderers(item, output))
    return
  }
  Object.values(node).forEach((value) => collectVideoRenderers(value, output))
}

const collectLockupViewModels = (node, output) => {
  if (!node || typeof node !== 'object') return
  if (node.lockupViewModel) {
    output.push(node.lockupViewModel)
    return
  }
  if (Array.isArray(node)) {
    node.forEach((item) => collectLockupViewModels(item, output))
    return
  }
  Object.values(node).forEach((value) => collectLockupViewModels(value, output))
}

const findWatchVideoId = (node) => {
  if (!node || typeof node !== 'object') return ''
  const videoId = node?.watchEndpoint?.videoId
  if (videoId) return String(videoId)

  if (Array.isArray(node)) {
    for (const item of node) {
      const nestedVideoId = findWatchVideoId(item)
      if (nestedVideoId) return nestedVideoId
    }
    return ''
  }

  for (const value of Object.values(node)) {
    const nestedVideoId = findWatchVideoId(value)
    if (nestedVideoId) return nestedVideoId
  }
  return ''
}

const extractOwnerProfile = (renderer) => {
  const ownerText = renderer?.ownerText || renderer?.longBylineText || renderer?.shortBylineText
  const name = pickText(ownerText)
  const ownerRun = Array.isArray(ownerText?.runs) ? ownerText.runs.find((run) => run?.navigationEndpoint) : null
  const browseEndpoint = ownerRun?.navigationEndpoint?.browseEndpoint
  const webUrl = ownerRun?.navigationEndpoint?.commandMetadata?.webCommandMetadata?.url
    || browseEndpoint?.canonicalBaseUrl
    || ''
  const avatar = pickThumbnail(
    renderer?.channelThumbnailSupportedRenderers?.channelThumbnailWithLinkRenderer?.thumbnail?.thumbnails
  )

  if (!name) return null

  return {
    id: browseEndpoint?.browseId || null,
    type: 'CHANNEL',
    name,
    url: normalizeUrl(webUrl, ORIGIN),
    avatar,
    is_nsfw: false,
  }
}

const getLockupMetadataParts = (lockup) => {
  const rows = lockup?.metadata?.lockupMetadataViewModel?.metadata?.contentMetadataViewModel?.metadataRows || []
  return rows.flatMap((row) => row?.metadataParts || [])
}

const findLockupOwnerRun = (lockup) => {
  const parts = getLockupMetadataParts(lockup)
  for (const part of parts) {
    const commandRuns = part?.text?.commandRuns || []
    const ownerRun = commandRuns.find((run) => run?.onTap?.innertubeCommand?.browseEndpoint)
    if (ownerRun) return ownerRun
  }
  return null
}

const extractLockupOwnerProfile = (lockup) => {
  const ownerRun = findLockupOwnerRun(lockup)
  const browseEndpoint = ownerRun?.onTap?.innertubeCommand?.browseEndpoint
  const webUrl = ownerRun?.onTap?.innertubeCommand?.commandMetadata?.webCommandMetadata?.url
    || browseEndpoint?.canonicalBaseUrl
    || ''
  const name = String(ownerRun?.text || '').trim()

  if (!name) return null

  return {
    id: browseEndpoint?.browseId || null,
    type: 'CHANNEL',
    name,
    url: normalizeUrl(webUrl, ORIGIN),
    avatar: '',
    is_nsfw: false,
  }
}

const durationTextPattern = /(?:^|\D)(\d{1,2}:\d{2}(?::\d{2})?)(?:\D|$)/

const extractDurationFromText = (value) => {
  const text = String(value || '')
  const duration = durationTextPattern.exec(text)?.[1] || ''
  return parseDuration(duration)
}

const extractLockupDuration = (lockup) => {
  const badges = lockup?.contentImage?.thumbnailViewModel?.overlays
    ?.flatMap((overlay) => overlay?.thumbnailBottomOverlayViewModel?.badges || [])
    || []
  for (const badge of badges) {
    const duration = parseDuration(badge?.thumbnailBadgeViewModel?.text)
    if (duration) return duration
  }

  const texts = getLockupMetadataParts(lockup).map((part) => part?.text?.content || '').filter(Boolean)
  for (const text of texts) {
    const duration = extractDurationFromText(text)
    if (duration) return duration
  }
  return null
}

const extractLockupPublishedText = (lockup) => {
  const texts = getLockupMetadataParts(lockup).map((part) => part?.text?.content || '').filter(Boolean)
  return texts.findLast((text) => /\b(?:ago|premiered|streamed|minutes?|hours?|days?|weeks?|months?|years?)\b/i.test(text)) || ''
}

const pickLockupThumbnail = (lockup) => {
  return pickThumbnail(
    lockup?.contentImage?.thumbnailViewModel?.image?.sources
    || lockup?.contentImage?.collectionThumbnailViewModel?.primaryThumbnail?.thumbnailViewModel?.image?.sources
  )
}

const mapVideoRenderer = (renderer) => {
  const videoId = String(renderer?.videoId || '').trim()
  const ownerProfile = extractOwnerProfile(renderer)
  return {
    source: 'remote',
    site: SITE,
    id: videoId,
    title: pickText(renderer?.title),
    url: videoId ? `${ORIGIN}/watch?v=${encodeURIComponent(videoId)}` : '',
    thumbnail: pickThumbnail(renderer?.thumbnail?.thumbnails),
    duration: parseDuration(pickText(renderer?.lengthText)),
    publish_date: null,
    published_text: pickText(renderer?.publishedTimeText),
    uploader: ownerProfile?.name || pickText(renderer?.ownerText),
    uploader_url: ownerProfile?.url || '',
    uploader_avatar: ownerProfile?.avatar || '',
    subscriptions: ownerProfile ? [ownerProfile] : [],
    description: pickText(renderer?.detailedMetadataSnippets?.[0]?.snippetText),
  }
}

const mapLockupViewModel = (lockup) => {
  const videoId = findWatchVideoId(lockup)
  const ownerProfile = extractLockupOwnerProfile(lockup)
  return {
    source: 'remote',
    site: SITE,
    id: videoId,
    title: lockup?.metadata?.lockupMetadataViewModel?.title?.content || '',
    url: videoId ? `${ORIGIN}/watch?v=${encodeURIComponent(videoId)}` : '',
    thumbnail: pickLockupThumbnail(lockup),
    duration: extractLockupDuration(lockup),
    publish_date: null,
    published_text: extractLockupPublishedText(lockup),
    uploader: ownerProfile?.name || '',
    uploader_url: ownerProfile?.url || '',
    uploader_avatar: ownerProfile?.avatar || '',
    subscriptions: ownerProfile ? [ownerProfile] : [],
    description: '',
  }
}

const mapYouTubeSearchItems = (payload) => {
  const renderers = []
  const lockups = []
  collectVideoRenderers(payload, renderers)
  collectLockupViewModels(payload, lockups)
  return uniqueByUrl([
    ...renderers.map((renderer) => mapVideoRenderer(renderer)),
    ...lockups.map((lockup) => mapLockupViewModel(lockup)),
  ]).filter((item) => item.id && item.title && item.url)
}

const mapYouTubeListItems = (items) => {
  return mapYouTubeSearchItems(items.filter((item) => !item?.continuationItemRenderer))
}

const extractApiKey = (html) => {
  return String(html.match(/"INNERTUBE_API_KEY"\s*:\s*"([^"]+)"/)?.[1] || '').trim()
}

const extractContext = (html) => {
  const jsonText = findBalancedJson(html, 'INNERTUBE_CONTEXT')
  if (!jsonText) throw new Error('YouTube context payload not found')
  return JSON.parse(jsonText)
}

const findContinuationToken = (items) => {
  const continuationItem = items.find((item) => item?.continuationItemRenderer)
  return String(
    continuationItem?.continuationItemRenderer?.continuationEndpoint?.continuationCommand?.token
    || ''
  ).trim()
}

const getInitialContinuationItems = (payload) => {
  return payload?.contents?.twoColumnSearchResultsRenderer?.primaryContents?.sectionListRenderer?.contents
    || payload?.contents?.sectionListRenderer?.contents
    || []
}

const getResponseContinuationItems = (payload) => {
  const commands = [
    ...(payload?.onResponseReceivedCommands || []),
    ...(payload?.onResponseReceivedActions || []),
  ]
  return commands.flatMap((command) => (
    command?.appendContinuationItemsAction?.continuationItems
    || command?.reloadContinuationItemsCommand?.continuationItems
    || []
  ))
}

const buildCursor = (continuation, apiKey, context) => {
  if (!continuation) return null
  const client = context?.client || {}
  return {
    continuation,
    api_key: apiKey,
    client: {
      clientName: client.clientName || 'WEB',
      clientVersion: client.clientVersion || '',
      hl: client.hl || 'en',
      gl: client.gl || 'US',
      userAgent: client.userAgent || DESKTOP_USER_AGENT,
      visitorData: client.visitorData || '',
    },
  }
}

const buildContinuationContext = (cursor) => {
  const client = cursor?.client || {}
  return {
    client: {
      clientName: client.clientName || 'WEB',
      clientVersion: client.clientVersion || '',
      hl: client.hl || 'en',
      gl: client.gl || 'US',
      userAgent: client.userAgent || DESKTOP_USER_AGENT,
      visitorData: client.visitorData || '',
    },
  }
}

const fetchContinuation = async ({ cursor, fetchImpl, buildCookieHeader, keyword }) => {
  const continuation = String(cursor?.continuation || '').trim()
  const apiKey = String(cursor?.api_key || '').trim()
  if (!continuation || !apiKey) {
    return null
  }

  const context = buildContinuationContext(cursor)
  const cookie = await buildCookieHeader(ORIGIN)
  const targetUrl = `${ORIGIN}/youtubei/v1/search?key=${encodeURIComponent(apiKey)}`
  const response = await fetchImpl(targetUrl, {
    method: 'POST',
    headers: {
      Accept: '*/*',
      'Content-Type': 'application/json',
      Origin: ORIGIN,
      Referer: `${ORIGIN}/results?search_query=${encodeURIComponent(keyword)}`,
      'Sec-Fetch-Mode': 'same-origin',
      'Sec-Fetch-Site': 'same-origin',
      'User-Agent': context.client.userAgent || DESKTOP_USER_AGENT,
      'X-Youtube-Bootstrap-Logged-In': 'false',
      'X-YouTube-Client-Name': '1',
      'X-YouTube-Client-Version': String(context.client.clientVersion || ''),
      ...(cookie ? { Cookie: cookie } : {}),
    },
    body: JSON.stringify({
      context,
      continuation,
    }),
  })
  if (!response.ok) throw new Error(`YouTube search continuation failed: ${response.status}`)
  return response.json()
}

export const searchYouTubeVideos = async ({ query, limit, page, fetchImpl, buildCookieHeader }) => {
  const keyword = normalizeQuery(query)
  if (!keyword) return { items: [], has_more: false }

  const resultLimit = clampLimit(limit)
  const resultPage = clampPage(page)

  const targetUrl = new URL('/results', ORIGIN)
  targetUrl.searchParams.set('search_query', keyword)

  const cookie = await buildCookieHeader(ORIGIN)
  const html = await fetchText(fetchImpl, targetUrl.toString(), {
    headers: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      Referer: `${ORIGIN}/`,
      'User-Agent': DESKTOP_USER_AGENT,
      ...(cookie ? { Cookie: cookie } : {}),
    },
  })

  const jsonText = findBalancedJson(html, 'ytInitialData')
  if (!jsonText) {
    throw new Error('YouTube search payload not found')
  }

  const initialData = JSON.parse(jsonText)
  const apiKey = extractApiKey(html)
  const context = extractContext(html)
  const initialItems = getInitialContinuationItems(initialData)
  let cursor = buildCursor(findContinuationToken(initialItems), apiKey, context)
  let items = mapYouTubeListItems(initialItems)
  const startIndex = (resultPage - 1) * resultLimit
  const endIndex = resultPage * resultLimit

  if (resultPage === 1) {
    return {
      items: items.slice(0, resultLimit),
      has_more: !!cursor,
    }
  }

  while (items.length < endIndex && cursor) {
    const payload = await fetchContinuation({
      cursor,
      fetchImpl,
      buildCookieHeader,
      keyword,
    })
    const continuationItems = getResponseContinuationItems(payload)
    items = uniqueByUrl([...items, ...mapYouTubeListItems(continuationItems)])
    cursor = buildCursor(findContinuationToken(continuationItems), cursor.api_key, { client: cursor.client })
  }

  return {
    items: items.slice(startIndex, endIndex),
    has_more: items.length > endIndex || !!cursor,
  }
}
