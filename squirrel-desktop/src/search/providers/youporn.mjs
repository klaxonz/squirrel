import { clampLimit, clampPage, decodeHtml, fetchText, normalizeQuery, normalizeUrl, parseDuration, stripHtml, uniqueByUrl } from './shared.mjs'

const SITE = 'youporn'
const ORIGIN = 'https://www.youporn.com'

const extractAttribute = (source, name) => {
  const match = source.match(new RegExp(`${name}=["']([^"']+)["']`, 'i'))
  return match ? decodeHtml(match[1]) : ''
}

const extractTitle = (block) => {
  const titleLink = block.match(/<a[^>]+class=["'][^"']*video-title-text[^"']*["'][^>]*>([\s\S]*?)<\/a>/i)
  return extractAttribute(block, 'aria-label') || stripHtml(titleLink?.[1] || '')
}

const extractThumbnail = (block) => {
  const image = block.match(/<img\b[^>]*>/i)?.[0] || ''
  for (const name of ['data-src', 'data-poster', 'src']) {
    const value = extractAttribute(image, name)
    if (!value || value.startsWith('data:')) continue

    const thumbnail = normalizeUrl(value, ORIGIN)
    if (!thumbnail) continue
    const url = new URL(thumbnail)
    const isImageFile = /\.(?:jpe?g|png|webp)(?:[?#]|$)/i.test(url.pathname)
    const isDynamicImage = url.hostname.endsWith('.ypncdn.com') && url.pathname.includes('/plain/')
    if (isImageFile || isDynamicImage) {
      return thumbnail
    }
  }

  return ''
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

  const cardPattern = /<article\b[^>]*class=["'][^"']*\bvideo-box\b[^"']*["'][^>]*>[\s\S]*?<\/article>/gi
  const items = []
  let match
  while ((match = cardPattern.exec(html)) && items.length < resultLimit * 3) {
    const block = match[0]
    const href = extractAttribute(block, 'href')
    const title = extractTitle(block)
    const thumbnail = extractThumbnail(block)
    const durationMatch = block.match(/class=["'][^"']*duration[^"']*["'][^>]*>\s*([^<]+)/i)
    const subscriptions = collectProfileLinks(block, /\/(?:channels|users)\//i, 'CHANNEL')
      .map((profile) => ({
        ...profile,
        is_nsfw: true,
      }))
    items.push({
      source: 'remote',
      site: SITE,
      id: href,
      title: stripHtml(title),
      url: normalizeUrl(href, ORIGIN),
      thumbnail,
      duration: parseDuration(durationMatch?.[1]),
      publish_date: null,
      uploader: subscriptions[0]?.name || '',
      uploader_url: subscriptions[0]?.url || '',
      uploader_avatar: '',
      subscriptions,
      actors: collectProfileLinks(block, /\/(?:pornstar|model)\//i, 'ACTOR'),
      description: '',
    })
  }

  return uniqueByUrl(items).filter((item) => item.title && item.url).slice(0, resultLimit)
}
