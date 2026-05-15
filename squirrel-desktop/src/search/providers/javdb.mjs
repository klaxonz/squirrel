import { clampLimit, fetchText, normalizeQuery, normalizeUrl, parseDuration, stripHtml, uniqueByUrl } from './shared.mjs'

const SITE = 'javdb'
const ORIGIN = 'https://javdb.com'

const extractAttribute = (source, name) => {
  const match = source.match(new RegExp(`${name}=["']([^"']+)["']`, 'i'))
  return match ? match[1] : ''
}

export const searchJavdbVideos = async ({ query, limit, fetchImpl, buildCookieHeader }) => {
  const keyword = normalizeQuery(query)
  if (!keyword) return []

  const resultLimit = clampLimit(limit)
  const targetUrl = new URL('/search', ORIGIN)
  targetUrl.searchParams.set('q', keyword)
  targetUrl.searchParams.set('f', 'all')

  const cookie = await buildCookieHeader(targetUrl.toString())
  const html = await fetchText(fetchImpl, targetUrl.toString(), {
    headers: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      Referer: `${ORIGIN}/`,
      ...(cookie ? { Cookie: cookie } : {}),
    },
  })

  const blocks = html.match(/<div[^>]+class=["'][^"']*item[^"']*["'][\s\S]*?<\/a>\s*<\/div>/gi) || []
  return uniqueByUrl(blocks.map((block) => {
    const hrefMatch = block.match(/href=["']([^"']*\/v\/[^"']+)["']/i)
    const titleMatch = block.match(/class=["'][^"']*video-title[^"']*["'][^>]*>\s*([^<]+)/i)
    const scoreMatch = block.match(/class=["'][^"']*score[^"']*["'][^>]*>\s*([^<]+)/i)
    return {
      source: 'remote',
      site: SITE,
      id: hrefMatch?.[1] || '',
      title: stripHtml(titleMatch?.[1]),
      url: normalizeUrl(hrefMatch?.[1] || '', ORIGIN),
      thumbnail: normalizeUrl(extractAttribute(block, 'src'), ORIGIN),
      duration: parseDuration(''),
      publish_date: null,
      uploader: stripHtml(scoreMatch?.[1]),
      description: '',
    }
  })).filter((item) => item.title && item.url).slice(0, resultLimit)
}
