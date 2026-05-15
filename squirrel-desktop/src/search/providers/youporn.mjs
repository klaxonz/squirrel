import { clampLimit, clampPage, fetchText, normalizeQuery, normalizeUrl, parseDuration, stripHtml, uniqueByUrl } from './shared.mjs'

const SITE = 'youporn'
const ORIGIN = 'https://www.youporn.com'

const extractAttribute = (source, name) => {
  const match = source.match(new RegExp(`${name}=["']([^"']+)["']`, 'i'))
  return match ? match[1] : ''
}

export const searchYouPornVideos = async ({ query, limit, page, fetchImpl, buildCookieHeader }) => {
  const keyword = normalizeQuery(query)
  if (!keyword) return []

  const resultLimit = clampLimit(limit)
  const resultPage = clampPage(page)
  const targetUrl = new URL('/search/', ORIGIN)
  targetUrl.searchParams.set('query', keyword)
  targetUrl.searchParams.set('page', String(resultPage))

  const cookie = await buildCookieHeader(targetUrl.toString())
  const html = await fetchText(fetchImpl, targetUrl.toString(), {
    headers: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      Referer: `${ORIGIN}/`,
      ...(cookie ? { Cookie: cookie } : {}),
    },
  })

  const anchorPattern = /<a[^>]+href=["'](\/watch\/[^"']+)["'][\s\S]*?<\/a>/gi
  const items = []
  let match
  while ((match = anchorPattern.exec(html)) && items.length < resultLimit * 3) {
    const start = Math.max(0, match.index - 800)
    const end = Math.min(html.length, anchorPattern.lastIndex + 1200)
    const block = html.slice(start, end)
    const title = extractAttribute(match[0], 'title') || extractAttribute(block, 'alt')
    const thumbnail = extractAttribute(block, 'data-src') || extractAttribute(block, 'src')
    const durationMatch = block.match(/class=["'][^"']*duration[^"']*["'][^>]*>\s*([^<]+)/i)
    items.push({
      source: 'remote',
      site: SITE,
      id: match[1],
      title: stripHtml(title),
      url: normalizeUrl(match[1], ORIGIN),
      thumbnail: normalizeUrl(thumbnail, ORIGIN),
      duration: parseDuration(durationMatch?.[1]),
      publish_date: null,
      uploader: '',
      description: '',
    })
  }

  return uniqueByUrl(items).filter((item) => item.title && item.url).slice(0, resultLimit)
}
