import { clampLimit, fetchText, normalizeQuery, normalizeUrl, parseDuration, stripHtml, uniqueByUrl } from './shared.mjs'

const SITE = 'pornhub'
const ORIGIN = 'https://www.pornhub.com'

const extractAttribute = (source, name) => {
  const match = source.match(new RegExp(`${name}=["']([^"']+)["']`, 'i'))
  return match ? match[1] : ''
}

export const searchPornhubVideos = async ({ query, limit, fetchImpl, buildCookieHeader }) => {
  const keyword = normalizeQuery(query)
  if (!keyword) return []

  const resultLimit = clampLimit(limit)
  const targetUrl = new URL('/video/search', ORIGIN)
  targetUrl.searchParams.set('search', keyword)

  const cookie = await buildCookieHeader(targetUrl.toString())
  const html = await fetchText(fetchImpl, targetUrl.toString(), {
    headers: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      Referer: `${ORIGIN}/`,
      ...(cookie ? { Cookie: cookie } : {}),
    },
  })

  const blocks = html.match(/<li[^>]+class=["'][^"']*(?:pcVideoListItem|videoblock)[^"']*["'][\s\S]*?<\/li>/gi) || []
  return uniqueByUrl(blocks.map((block) => {
    const hrefMatch = block.match(/href=["']([^"']*view_video\.php\?viewkey=[^"']+)["']/i)
    const title = extractAttribute(block, 'data-title') || extractAttribute(block, 'title')
    const thumbnail = extractAttribute(block, 'data-mediumthumb')
      || extractAttribute(block, 'data-src')
      || extractAttribute(block, 'src')
    const durationMatch = block.match(/class=["'][^"']*duration[^"']*["'][^>]*>\s*([^<]+)/i)
    const uploaderMatch = block.match(/class=["'][^"']*usernameWrap[^"']*["'][\s\S]*?>([\s\S]*?)<\/a>/i)
    return {
      source: 'remote',
      site: SITE,
      id: extractAttribute(block, 'data-video-vkey') || hrefMatch?.[1] || '',
      title: stripHtml(title),
      url: normalizeUrl(hrefMatch?.[1] || '', ORIGIN),
      thumbnail: normalizeUrl(thumbnail, ORIGIN),
      duration: parseDuration(durationMatch?.[1]),
      publish_date: null,
      uploader: stripHtml(uploaderMatch?.[1]),
      description: '',
    }
  })).filter((item) => item.title && item.url).slice(0, resultLimit)
}
