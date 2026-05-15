import { clampLimit, clampPage, normalizeQuery, normalizeUrl, parseDuration, stripHtml, uniqueByUrl } from './shared.mjs'

const SITE = 'javdb'
const ORIGIN = 'https://javdb.com'

const extractAttribute = (source, name) => {
  const match = source.match(new RegExp(`${name}=["']([^"']+)["']`, 'i'))
  return match ? match[1] : ''
}

export const searchJavdbVideos = async ({ query, limit, page, loadDocumentHtml }) => {
  const keyword = normalizeQuery(query)
  if (!keyword) return []
  if (typeof loadDocumentHtml !== 'function') {
    throw new Error('JavDB search requires browser document loading')
  }

  const resultLimit = clampLimit(limit)
  const resultPage = clampPage(page)
  const targetUrl = new URL('/search', ORIGIN)
  targetUrl.searchParams.set('q', keyword)
  targetUrl.searchParams.set('f', 'all')
  targetUrl.searchParams.set('page', String(resultPage))

  const html = await loadDocumentHtml(targetUrl.toString(), {
    timeoutMs: 30000,
    challengeTimeoutMs: 60000,
  })

  const blocks = html.match(/<div[^>]+class=["'][^"']*item[^"']*["'][\s\S]*?<\/a>\s*<\/div>/gi) || []
  return uniqueByUrl(blocks.map((block) => {
    const hrefMatch = block.match(/href=["']([^"']*\/v\/[^"']+)["']/i)
    const titleMatch = block.match(/class=["'][^"']*video-title[^"']*["'][^>]*>([\s\S]*?)<\/div>/i)
    const scoreMatch = block.match(/class=["'][^"']*score[^"']*["'][\s\S]*?class=["'][^"']*value[^"']*["'][^>]*>([\s\S]*?)<\/span>/i)
    const metaMatch = block.match(/class=["'][^"']*meta[^"']*["'][^>]*>\s*([^<]+)/i)
    return {
      source: 'remote',
      site: SITE,
      id: hrefMatch?.[1] || '',
      title: stripHtml(titleMatch?.[1]),
      url: normalizeUrl(hrefMatch?.[1] || '', ORIGIN),
      thumbnail: normalizeUrl(extractAttribute(block, 'src'), ORIGIN),
      duration: parseDuration(''),
      publish_date: stripHtml(metaMatch?.[1]) || null,
      uploader: stripHtml(scoreMatch?.[1]),
      description: '',
    }
  })).filter((item) => item.title && item.url).slice(0, resultLimit)
}
