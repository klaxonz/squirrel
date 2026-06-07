import { clampLimit, clampPage, normalizeQuery, normalizeUrl, parseDuration, stripHtml, uniqueByUrl } from './shared.mjs'

import { desktopChromeUserAgent } from '../../constants.mjs'

const SITE = 'bilibili'
const ORIGIN = 'https://www.bilibili.com'
const USER_AGENT = desktopChromeUserAgent

const loadUploaderProfile = async ({ mid, fetchImpl, cookie }) => {
  if (!mid) return null

  const profileUrl = new URL('https://api.bilibili.com/x/web-interface/card')
  profileUrl.searchParams.set('mid', String(mid))
  const response = await fetchImpl(profileUrl.toString(), {
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
    return null
  }

  const payload = await response.json()
  const card = payload?.data?.card || null
  if (!card) return null

  return {
    name: stripHtml(card?.name),
    avatar: normalizeUrl(card?.face || '', ORIGIN),
  }
}

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
  const items = await Promise.all(rows.map(async (row) => {
    const uploader = stripHtml(row?.author)
    const uploaderId = row?.mid || row?.up_id || null
    const uploaderUrl = uploaderId ? `https://space.bilibili.com/${uploaderId}` : ''
    let uploaderName = uploader
    let uploaderAvatar = normalizeUrl(row?.upic || '', ORIGIN)
    if (uploaderId && !uploaderAvatar) {
      const profile = await loadUploaderProfile({ mid: uploaderId, fetchImpl, cookie })
      uploaderName = profile?.name || uploaderName
      uploaderAvatar = profile?.avatar || uploaderAvatar
    }

    const subscription = uploaderName ? {
      id: uploaderId,
      type: 'CHANNEL',
      name: uploaderName,
      url: uploaderUrl,
      avatar: uploaderAvatar,
      is_nsfw: false,
    } : null

    return {
      source: 'remote',
      site: SITE,
      id: row?.bvid || row?.aid || row?.id || row?.arcurl,
      title: stripHtml(row?.title),
      url: normalizeUrl(row?.arcurl || (row?.bvid ? `/video/${row.bvid}` : ''), ORIGIN),
      thumbnail: normalizeUrl(row?.pic || '', ORIGIN),
      duration: parseDuration(row?.duration),
      publish_date: row?.pubdate ? new Date(Number(row.pubdate) * 1000).toISOString() : null,
      uploader: uploaderName,
      uploader_url: uploaderUrl,
      uploader_avatar: uploaderAvatar,
      subscriptions: subscription ? [subscription] : [],
      description: stripHtml(row?.description),
    }
  }))
  return uniqueByUrl(items).filter((item) => item.title && item.url).slice(0, resultLimit)
}
