import {
  clampLimit,
  clampPage,
  fetchText,
  findBalancedJson,
  normalizeQuery,
  uniqueByUrl,
} from './shared.mjs'
import {
  collectVideoRenderers,
  collectLockupViewModels,
  extractApiKey,
  extractContext,
  findContinuationToken,
  buildCursor,
  buildContinuationContext,
  mapVideoRenderer,
  mapLockupViewModel,
  YOUTUBE_ORIGIN,
} from './youtube-shared.mjs'
import { desktopChromeUserAgent } from '../../constants.mjs'

const SITE = 'youtube'
const DESKTOP_USER_AGENT = desktopChromeUserAgent

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

const mapYouTubeSearchItems = (payload) => {
  const renderers = []
  const lockups = []
  collectVideoRenderers(payload, renderers)
  collectLockupViewModels(payload, lockups)
  return uniqueByUrl([
    ...renderers.map((r) => ({ ...mapVideoRenderer(r), site: SITE })),
    ...lockups.map((l) => ({ ...mapLockupViewModel(l), site: SITE })),
  ]).filter((item) => item.id && item.title && item.url)
}

const mapYouTubeListItems = (items) => {
  return mapYouTubeSearchItems(items.filter((item) => !item?.continuationItemRenderer))
}

const fetchContinuation = async ({ cursor, fetchImpl, buildCookieHeader, keyword }) => {
  const continuation = String(cursor?.continuation || '').trim()
  const apiKey = String(cursor?.api_key || '').trim()
  if (!continuation || !apiKey) return null

  const context = buildContinuationContext(cursor)
  const cookie = await buildCookieHeader(YOUTUBE_ORIGIN)
  const targetUrl = `${YOUTUBE_ORIGIN}/youtubei/v1/search?key=${encodeURIComponent(apiKey)}`
  const response = await fetchImpl(targetUrl, {
    method: 'POST',
    headers: {
      Accept: '*/*',
      'Content-Type': 'application/json',
      Origin: YOUTUBE_ORIGIN,
      Referer: `${YOUTUBE_ORIGIN}/results?search_query=${encodeURIComponent(keyword)}`,
      'Sec-Fetch-Mode': 'same-origin',
      'Sec-Fetch-Site': 'same-origin',
      'User-Agent': context.client.userAgent || DESKTOP_USER_AGENT,
      'X-Youtube-Bootstrap-Logged-In': 'false',
      'X-YouTube-Client-Name': '1',
      'X-YouTube-Client-Version': String(context.client.clientVersion || ''),
      ...(cookie ? { Cookie: cookie } : {}),
    },
    body: JSON.stringify({ context, continuation }),
  })
  if (!response.ok) throw new Error(`YouTube search continuation failed: ${response.status}`)
  return response.json()
}

export const searchYouTubeVideos = async ({ query, limit, page, fetchImpl, buildCookieHeader }) => {
  const keyword = normalizeQuery(query)
  if (!keyword) return { items: [], has_more: false }

  const resultLimit = clampLimit(limit)
  const resultPage = clampPage(page)

  const targetUrl = new URL('/results', YOUTUBE_ORIGIN)
  targetUrl.searchParams.set('search_query', keyword)

  const cookie = await buildCookieHeader(YOUTUBE_ORIGIN)
  const html = await fetchText(fetchImpl, targetUrl.toString(), {
    headers: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      Referer: `${YOUTUBE_ORIGIN}/`,
      'User-Agent': DESKTOP_USER_AGENT,
      ...(cookie ? { Cookie: cookie } : {}),
    },
  })

  const jsonText = findBalancedJson(html, 'ytInitialData')
  if (!jsonText) throw new Error('YouTube search payload not found')

  const initialData = JSON.parse(jsonText)
  const apiKey = extractApiKey(html)
  const context = extractContext(html)
  const initialItems = getInitialContinuationItems(initialData)
  let cursor = buildCursor(findContinuationToken(initialItems), apiKey, context)
  let items = mapYouTubeListItems(initialItems)
  const startIndex = (resultPage - 1) * resultLimit
  const endIndex = resultPage * resultLimit

  if (resultPage === 1) {
    return { items: items.slice(0, resultLimit), has_more: !!cursor }
  }

  while (items.length < endIndex && cursor) {
    const payload = await fetchContinuation({ cursor, fetchImpl, buildCookieHeader, keyword })
    const continuationItems = getResponseContinuationItems(payload)
    items = uniqueByUrl([...items, ...mapYouTubeListItems(continuationItems)])
    cursor = buildCursor(findContinuationToken(continuationItems), cursor.api_key, { client: cursor.client })
  }

  return {
    items: items.slice(startIndex, endIndex),
    has_more: items.length > endIndex || !!cursor,
  }
}
