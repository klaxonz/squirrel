import {
  clampLimit,
  fetchText,
  findBalancedJson,
  normalizeQuery,
  parseDuration,
  pickText,
  pickThumbnail,
  uniqueByUrl,
} from './shared.mjs'

const SITE = 'youtube'
const ORIGIN = 'https://www.youtube.com'

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

export const searchYouTubeVideos = async ({ query, limit, page, fetchImpl, buildCookieHeader }) => {
  const keyword = normalizeQuery(query)
  if (!keyword) return []

  const resultLimit = clampLimit(limit)
  if (Number(page || 1) > 1) return []

  const targetUrl = new URL('/results', ORIGIN)
  targetUrl.searchParams.set('search_query', keyword)

  const cookie = await buildCookieHeader(ORIGIN)
  const html = await fetchText(fetchImpl, targetUrl.toString(), {
    headers: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      Referer: `${ORIGIN}/`,
      ...(cookie ? { Cookie: cookie } : {}),
    },
  })

  const jsonText = findBalancedJson(html, 'ytInitialData')
  if (!jsonText) {
    throw new Error('YouTube search payload not found')
  }

  const initialData = JSON.parse(jsonText)
  const renderers = []
  collectVideoRenderers(initialData, renderers)

  return uniqueByUrl(renderers.map((renderer) => {
    const videoId = String(renderer?.videoId || '').trim()
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
      uploader: pickText(renderer?.ownerText),
      description: pickText(renderer?.detailedMetadataSnippets?.[0]?.snippetText),
    }
  })).filter((item) => item.id && item.title && item.url).slice(0, resultLimit)
}
