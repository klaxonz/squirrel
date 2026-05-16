import { clampLimit, clampPage, fetchText, normalizeQuery, normalizeUrl, parseDuration, stripHtml, uniqueByUrl } from './shared.mjs'

const SITE = 'pornhub'
const ORIGIN = 'https://www.pornhub.com'

const extractAttribute = (source, name) => {
  const match = source.match(new RegExp(`${name}=["']([^"']+)["']`, 'i'))
  return match ? match[1] : ''
}

const collectProfileLinks = (block, hrefPattern, type) => {
  const profiles = []
  const seen = new Set()
  const linkPattern = /<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi
  let match
  while ((match = linkPattern.exec(block))) {
    if (!hrefPattern.test(match[1])) continue
    const url = normalizeUrl(match[1], ORIGIN)
    const name = stripHtml(match[2])
    const key = `${name}:${url}`
    if (!name || !url || seen.has(key)) continue
    seen.add(key)
    profiles.push({
      type,
      name,
      url,
      avatar: '',
    })
  }
  return profiles
}

export const searchPornhubVideos = async ({ query, limit, page, fetchImpl, buildCookieHeader }) => {
  const keyword = normalizeQuery(query)
  if (!keyword) return []

  const resultLimit = clampLimit(limit)
  const resultPage = clampPage(page)
  const targetUrl = new URL('/video/search', ORIGIN)
  targetUrl.searchParams.set('search', keyword)
  targetUrl.searchParams.set('page', String(resultPage))

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
    const uploaderLink = block.match(/class=["'][^"']*usernameWrap[^"']*["'][\s\S]*?<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/i)
    const uploader = stripHtml(uploaderLink?.[2])
    const uploaderUrl = normalizeUrl(uploaderLink?.[1] || '', ORIGIN)
    const subscription = uploader ? {
      type: 'CHANNEL',
      name: uploader,
      url: uploaderUrl,
      avatar: '',
      is_nsfw: true,
    } : null
    return {
      source: 'remote',
      site: SITE,
      id: extractAttribute(block, 'data-video-vkey') || hrefMatch?.[1] || '',
      title: stripHtml(title),
      url: normalizeUrl(hrefMatch?.[1] || '', ORIGIN),
      thumbnail: normalizeUrl(thumbnail, ORIGIN),
      duration: parseDuration(durationMatch?.[1]),
      publish_date: null,
      uploader,
      uploader_url: uploaderUrl,
      uploader_avatar: '',
      subscriptions: subscription ? [subscription] : [],
      actors: collectProfileLinks(block, /\/(?:pornstar|model)\//i, 'ACTOR'),
      description: '',
    }
  })).filter((item) => item.title && item.url).slice(0, resultLimit)
}
