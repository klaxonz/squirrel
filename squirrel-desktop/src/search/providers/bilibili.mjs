import { clampLimit, clampPage, normalizeQuery, normalizeUrl, parseDuration, stripHtml, uniqueByUrl } from './shared.mjs'

const SITE = 'bilibili'
const ORIGIN = 'https://www.bilibili.com'
const USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'

export const searchBilibiliVideos = async ({ query, limit, page, fetchImpl, buildCookieHeader }) => {
  const keyword = normalizeQuery(query)
  if (!keyword) return []

  const resultLimit = clampLimit(limit)
  const resultPage = clampPage(page)
  const apiUrl = new URL('https://api.bilibili.com/x/web-interface/search/type')
  apiUrl.searchParams.set('search_type', 'video')
  apiUrl.searchParams.set('keyword', keyword)
  apiUrl.searchParams.set('page', String(resultPage))
  apiUrl.searchParams.set('page_size', String(resultLimit))

  const cookie = await buildCookieHeader(ORIGIN)
  const response = await fetchImpl(apiUrl.toString(), {
    headers: {
      Accept: 'application/json, text/plain, */*',
      'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
      Referer: `${ORIGIN}/`,
      Origin: ORIGIN,
      'User-Agent': USER_AGENT,
      ...(cookie ? { Cookie: cookie } : {}),
    },
  })
  if (!response.ok) {
    throw new Error(`Bilibili search failed: ${response.status}`)
  }

  const payload = await response.json()
  const rows = Array.isArray(payload?.data?.result) ? payload.data.result : []
  return uniqueByUrl(rows.map((row) => ({
    source: 'remote',
    site: SITE,
    id: row?.bvid || row?.aid || row?.id || row?.arcurl,
    title: stripHtml(row?.title),
    url: normalizeUrl(row?.arcurl || (row?.bvid ? `/video/${row.bvid}` : ''), ORIGIN),
    thumbnail: normalizeUrl(row?.pic || '', ORIGIN),
    duration: parseDuration(row?.duration),
    publish_date: row?.pubdate ? new Date(Number(row.pubdate) * 1000).toISOString() : null,
    uploader: stripHtml(row?.author),
    description: stripHtml(row?.description),
  }))).filter((item) => item.title && item.url).slice(0, resultLimit)
}
