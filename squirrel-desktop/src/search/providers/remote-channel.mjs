import { createHash } from 'node:crypto'

import {
  clampLimit,
  clampPage,
  fetchText,
  findBalancedJson,
  normalizeUrl,
  parseDuration,
  pickText,
  pickThumbnail,
  stripHtml,
  uniqueByUrl,
} from './shared.mjs'

const BILIBILI_ORIGIN = 'https://www.bilibili.com'
const BILIBILI_SPACE_ORIGIN = 'https://space.bilibili.com'
const YOUTUBE_ORIGIN = 'https://www.youtube.com'
const PORNHUB_ORIGIN = 'https://www.pornhub.com'
const YOUPORN_ORIGIN = 'https://www.youporn.com'
const DESKTOP_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
const BILIBILI_WEB_LOCATION_SPACE = '1550101'
const WBI_MIXIN_KEY_ENC_TAB = [
  46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
  33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
  61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
  36, 20, 34, 44, 52,
]

const SITE_ALIASES = {
  'bilibili.com': 'bilibili',
  'b23.tv': 'bilibili',
  'youtube.com': 'youtube',
  'youtu.be': 'youtube',
  'pornhub.com': 'pornhub',
  'youporn.com': 'youporn',
}

const normalizeSite = (site, targetUrl) => {
  const rawSite = String(site || '').trim().toLowerCase()
  if (rawSite && rawSite !== 'all') return SITE_ALIASES[rawSite.replace(/^www\./, '')] || rawSite

  const hostname = new URL(targetUrl).hostname.toLowerCase().replace(/^www\./, '')
  return SITE_ALIASES[hostname] || hostname
}

const extractAttribute = (source, name) => {
  const match = String(source || '').match(new RegExp(`${name}=["']([^"']+)["']`, 'i'))
  return match ? match[1] : ''
}

const buildBilibiliHeaders = (cookie) => ({
  Accept: 'application/json, text/plain, */*',
  'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
  'Cache-Control': 'no-cache',
  Pragma: 'no-cache',
  Referer: `${BILIBILI_ORIGIN}/`,
  Origin: BILIBILI_ORIGIN,
  'Sec-Ch-Ua': '"Chromium";v="135", "Not-A.Brand";v="8"',
  'Sec-Ch-Ua-Mobile': '?0',
  'Sec-Ch-Ua-Platform': '"Windows"',
  'Sec-Fetch-Dest': 'empty',
  'Sec-Fetch-Mode': 'cors',
  'Sec-Fetch-Site': 'same-site',
  'User-Agent': DESKTOP_USER_AGENT,
  ...(cookie ? { Cookie: cookie } : {}),
})

const fetchBilibiliJson = async (fetchImpl, targetUrl, cookie) => {
  const response = await fetchImpl(targetUrl, {
    headers: buildBilibiliHeaders(cookie),
  })
  if (!response.ok) throw new Error(`Bilibili request failed: ${response.status}`)

  const payload = await response.json()
  if (payload?.code !== undefined && payload.code !== 0) {
    if (payload.code === -101 && payload?.data?.wbi_img) {
      return payload.data
    }
    throw new Error(`${payload?.message || payload?.msg || payload.code} (code=${payload.code})`)
  }
  return payload?.data || {}
}

const getMixinKey = (value) => {
  return WBI_MIXIN_KEY_ENC_TAB
    .map((index) => value[index] || '')
    .join('')
    .slice(0, 32)
}

const signBilibiliWbiParams = (params, { imgKey, subKey }) => {
  if (!imgKey || !subKey) throw new Error('Bilibili WBI keys are missing')

  const mixinKey = getMixinKey(`${imgKey}${subKey}`)
  const signedParams = {
    ...params,
    wts: String(Math.round(Date.now() / 1000)),
  }
  const sortedEntries = Object.entries(signedParams)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => [
      key,
      String(value).replace(/[!'()*]/g, ''),
    ])
  const query = new URLSearchParams(sortedEntries).toString()
  const wRid = createHash('md5').update(`${query}${mixinKey}`).digest('hex')
  return {
    ...Object.fromEntries(sortedEntries),
    w_rid: wRid,
  }
}

const normalizeChannelUrl = (value) => {
  const url = normalizeUrl(value, YOUTUBE_ORIGIN)
  if (!url) throw new Error('Remote channel URL is required')
  return url
}

const collectYouTubeVideoRenderers = (node, output) => {
  if (!node || typeof node !== 'object') return
  if (node.videoRenderer) {
    output.push(node.videoRenderer)
    return
  }
  if (Array.isArray(node)) {
    node.forEach((item) => collectYouTubeVideoRenderers(item, output))
    return
  }
  Object.values(node).forEach((value) => collectYouTubeVideoRenderers(value, output))
}

const collectYouTubeLockupViewModels = (node, output) => {
  if (!node || typeof node !== 'object') return
  if (node.lockupViewModel) {
    output.push(node.lockupViewModel)
    return
  }
  if (Array.isArray(node)) {
    node.forEach((item) => collectYouTubeLockupViewModels(item, output))
    return
  }
  Object.values(node).forEach((value) => collectYouTubeLockupViewModels(value, output))
}

const findYouTubeContinuationToken = (node) => {
  if (!node || typeof node !== 'object') return ''
  const token = node?.continuationCommand?.token
    || node?.nextContinuationData?.continuation
    || node?.reloadContinuationData?.continuation
  if (token) return String(token)

  if (Array.isArray(node)) {
    for (const item of node) {
      const nestedToken = findYouTubeContinuationToken(item)
      if (nestedToken) return nestedToken
    }
    return ''
  }

  for (const value of Object.values(node)) {
    const nestedToken = findYouTubeContinuationToken(value)
    if (nestedToken) return nestedToken
  }
  return ''
}

const buildYouTubeVideosUrl = (channelUrl) => {
  const url = new URL(channelUrl)
  if (!url.pathname.endsWith('/videos')) {
    url.pathname = `${url.pathname.replace(/\/$/, '')}/videos`
  }
  return url.toString()
}

const extractYouTubeProfile = (initialData, channelUrl, providedProfile = {}) => {
  const metadata = initialData?.metadata?.channelMetadataRenderer || {}
  const header = initialData?.header?.pageHeaderRenderer || initialData?.header?.c4TabbedHeaderRenderer || {}
  const avatar = pickThumbnail(
    header?.image?.decoratedAvatarViewModel?.avatar?.avatarViewModel?.image?.sources
    || header?.avatar?.thumbnails
    || metadata?.avatar?.thumbnails
  )
  const name = metadata?.title || pickText(header?.title) || providedProfile.name || ''

  return {
    id: metadata?.externalId || providedProfile.id || null,
    type: 'CHANNEL',
    name,
    url: channelUrl,
    avatar: avatar || providedProfile.avatar || '',
    description: metadata?.description || '',
    site: 'youtube',
    is_nsfw: false,
  }
}

const mapYouTubeVideo = (renderer, profile) => {
  const videoId = String(renderer?.videoId || '').trim()
  return {
    source: 'remote',
    site: 'youtube',
    id: videoId,
    title: pickText(renderer?.title),
    url: videoId ? `${YOUTUBE_ORIGIN}/watch?v=${encodeURIComponent(videoId)}` : '',
    thumbnail: pickThumbnail(renderer?.thumbnail?.thumbnails),
    duration: parseDuration(pickText(renderer?.lengthText)),
    publish_date: null,
    published_text: pickText(renderer?.publishedTimeText),
    uploader: profile.name,
    uploader_url: profile.url,
    uploader_avatar: profile.avatar,
    subscriptions: [profile],
    description: pickText(renderer?.detailedMetadataSnippets?.[0]?.snippetText),
  }
}

const findYouTubeWatchVideoId = (node) => {
  if (!node || typeof node !== 'object') return ''
  const videoId = node?.watchEndpoint?.videoId
  if (videoId) return String(videoId)

  if (Array.isArray(node)) {
    for (const item of node) {
      const nestedVideoId = findYouTubeWatchVideoId(item)
      if (nestedVideoId) return nestedVideoId
    }
    return ''
  }

  for (const value of Object.values(node)) {
    const nestedVideoId = findYouTubeWatchVideoId(value)
    if (nestedVideoId) return nestedVideoId
  }
  return ''
}

const extractYouTubeLockupDuration = (lockup) => {
  const badges = lockup?.contentImage?.thumbnailViewModel?.overlays
    ?.flatMap((overlay) => overlay?.thumbnailBottomOverlayViewModel?.badges || [])
    || []
  for (const badge of badges) {
    const duration = parseDuration(badge?.thumbnailBadgeViewModel?.text)
    if (duration) return duration
  }
  return null
}

const extractYouTubeLockupPublishedText = (lockup) => {
  const rows = lockup?.metadata?.lockupMetadataViewModel?.metadata?.contentMetadataViewModel?.metadataRows || []
  const parts = rows.flatMap((row) => row?.metadataParts || [])
  const texts = parts.map((part) => part?.text?.content || '').filter(Boolean)
  return texts[texts.length - 1] || ''
}

const mapYouTubeLockup = (lockup, profile) => {
  const videoId = findYouTubeWatchVideoId(lockup)
  return {
    source: 'remote',
    site: 'youtube',
    id: videoId,
    title: lockup?.metadata?.lockupMetadataViewModel?.title?.content || '',
    url: videoId ? `${YOUTUBE_ORIGIN}/watch?v=${encodeURIComponent(videoId)}` : '',
    thumbnail: pickThumbnail(lockup?.contentImage?.thumbnailViewModel?.image?.sources),
    duration: extractYouTubeLockupDuration(lockup),
    publish_date: null,
    published_text: extractYouTubeLockupPublishedText(lockup),
    uploader: profile.name,
    uploader_url: profile.url,
    uploader_avatar: profile.avatar,
    subscriptions: [profile],
    description: '',
  }
}

const mapYouTubeItems = (payload, profile) => {
  const renderers = []
  const lockups = []
  collectYouTubeVideoRenderers(payload, renderers)
  collectYouTubeLockupViewModels(payload, lockups)
  return uniqueByUrl([
    ...renderers.map((renderer) => mapYouTubeVideo(renderer, profile)),
    ...lockups.map((lockup) => mapYouTubeLockup(lockup, profile)),
  ]).filter((item) => item.id && item.title && item.url)
}

const extractYouTubeApiKey = (html) => {
  return String(html.match(/"INNERTUBE_API_KEY"\s*:\s*"([^"]+)"/)?.[1] || '').trim()
}

const extractYouTubeContext = (html) => {
  const jsonText = findBalancedJson(html, 'INNERTUBE_CONTEXT')
  if (!jsonText) throw new Error('YouTube context payload not found')
  return JSON.parse(jsonText)
}

const buildYouTubeCursor = (continuation, apiKey, context) => {
  if (!continuation) return null
  const client = context?.client || {}
  return {
    continuation,
    api_key: apiKey,
    client: {
      clientName: client.clientName || 'WEB',
      clientVersion: client.clientVersion || '',
      hl: client.hl || 'en',
      gl: client.gl || 'US',
      userAgent: client.userAgent || DESKTOP_USER_AGENT,
      visitorData: client.visitorData || '',
    },
  }
}

const buildYouTubeContinuationContext = (cursor) => {
  const client = cursor?.client || cursor?.context?.client || {}
  return {
    client: {
      clientName: client.clientName || 'WEB',
      clientVersion: client.clientVersion || '',
      hl: client.hl || 'en',
      gl: client.gl || 'US',
      userAgent: client.userAgent || DESKTOP_USER_AGENT,
      visitorData: client.visitorData || '',
    },
  }
}

const fetchYouTubeContinuation = async ({ cursor, fetchImpl, buildCookieHeader }) => {
  const continuation = String(cursor?.continuation || '').trim()
  const apiKey = String(cursor?.api_key || '').trim()
  if (!continuation || !apiKey) {
    throw new Error('YouTube continuation cursor is missing')
  }

  const cookie = await buildCookieHeader(YOUTUBE_ORIGIN)
  const context = buildYouTubeContinuationContext(cursor)
  const response = await fetchImpl(`${YOUTUBE_ORIGIN}/youtubei/v1/browse?key=${encodeURIComponent(apiKey)}`, {
    method: 'POST',
    headers: {
      Accept: '*/*',
      'Content-Type': 'application/json',
      Origin: YOUTUBE_ORIGIN,
      Referer: `${YOUTUBE_ORIGIN}/`,
      'Sec-Fetch-Mode': 'same-origin',
      'Sec-Fetch-Site': 'same-origin',
      'User-Agent': context.client.userAgent || DESKTOP_USER_AGENT,
      'X-Youtube-Bootstrap-Logged-In': 'false',
      'X-YouTube-Client-Name': '1',
      'X-YouTube-Client-Version': String(context?.client?.clientVersion || ''),
      ...(cookie ? { Cookie: cookie } : {}),
    },
    body: JSON.stringify({
      context,
      continuation,
    }),
  })
  if (!response.ok) throw new Error(`YouTube channel continuation failed: ${response.status}`)
  return response.json()
}

const getYouTubeChannel = async ({ url, limit, page, cursor, fetchImpl, buildCookieHeader, profile }) => {
  const resultLimit = clampLimit(limit)
  const resultPage = clampPage(page)

  if (resultPage > 1) {
    const payload = await fetchYouTubeContinuation({ cursor, fetchImpl, buildCookieHeader })
    const channelProfile = {
      ...profile,
      type: 'CHANNEL',
      site: 'youtube',
      is_nsfw: false,
    }
    const continuation = findYouTubeContinuationToken(payload)
    const items = mapYouTubeItems(payload, channelProfile)

    return {
      profile: channelProfile,
      items: items.slice(0, resultLimit),
      page: resultPage,
      has_more: !!continuation,
      next_cursor: continuation ? { ...cursor, continuation } : null,
    }
  }

  const channelUrl = normalizeChannelUrl(url)
  const videosUrl = buildYouTubeVideosUrl(channelUrl)
  const cookie = await buildCookieHeader(YOUTUBE_ORIGIN)
  const html = await fetchText(fetchImpl, videosUrl, {
    headers: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      Referer: `${YOUTUBE_ORIGIN}/`,
      ...(cookie ? { Cookie: cookie } : {}),
    },
  })
  const jsonText = findBalancedJson(html, 'ytInitialData')
  if (!jsonText) throw new Error('YouTube channel payload not found')

  const initialData = JSON.parse(jsonText)
  const apiKey = extractYouTubeApiKey(html)
  const context = extractYouTubeContext(html)
  const channelProfile = extractYouTubeProfile(initialData, channelUrl, profile)
  const continuation = findYouTubeContinuationToken(initialData)
  const items = mapYouTubeItems(initialData, channelProfile)

  return {
    profile: channelProfile,
    items: items.slice(0, resultLimit),
    page: 1,
    has_more: !!continuation,
    next_cursor: buildYouTubeCursor(continuation, apiKey, context),
  }
}

const extractBilibiliMid = (targetUrl) => {
  const pathname = new URL(targetUrl).pathname
  const match = pathname.match(/^\/(\d+)/)
  if (!match) throw new Error('Bilibili channel id not found')
  return match[1]
}

const readBilibiliSpacePageValue = async ({ mid, page, loadDocumentHtml, script, evaluatePage }) => {
  if (typeof loadDocumentHtml !== 'function') {
    throw new Error('Bilibili remote channel requires browser document loading')
  }

  const spaceUrl = new URL(`https://space.bilibili.com/${mid}/video`)
  if (page > 1) spaceUrl.searchParams.set('pn', String(page))

  return loadDocumentHtml(spaceUrl.toString(), {
    timeoutMs: 45000,
    evaluateScript: script,
    evaluatePage,
  })
}

const fetchBilibiliSpacePageJson = async ({ mid, page, baseParams, imgKey, subKey, loadDocumentHtml }) => {
  const result = await readBilibiliSpacePageValue({
    mid,
    page,
    loadDocumentHtml,
    evaluatePage: async (evaluate) => {
      const riskParams = await evaluate(`
        (async () => {
          const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
          for (let index = 0; index < 80; index += 1) {
            if (window.__biliUserFp__) break;
            await delay(100);
          }
          const result = {};
          if (window.__biliUserFp__?.queryUserLog) {
            const values = window.__biliUserFp__.queryUserLog(${JSON.stringify(baseParams)});
            if (values?.[0]) result.dm_img_list = values[0];
            if (values?.[1]) result.dm_img_str = values[1];
            if (values?.[2]) result.dm_cover_img_str = values[2];
            if (values?.[3]) result.dm_img_inter = values[3];
          }
          if (window._render_data_?.access_id) result.w_webid = window._render_data_.access_id;
          return result;
        })()
      `)
      const normalizedRiskParams = !riskParams || typeof riskParams !== 'object'
        ? {}
        : Object.fromEntries(Object.entries(riskParams)
          .map(([key, value]) => [key, String(value || '').trim()])
          .filter(([, value]) => value))
      const signedParams = signBilibiliWbiParams({
        ...baseParams,
        ...normalizedRiskParams,
      }, {
        imgKey,
        subKey,
      })
      const videosUrl = new URL('https://api.bilibili.com/x/space/wbi/arc/search')
      for (const [key, value] of Object.entries(signedParams)) {
        videosUrl.searchParams.set(key, value)
      }

      return evaluate(`
        (async () => {
          const response = await fetch(${JSON.stringify(videosUrl.toString())}, {
            credentials: 'include',
            headers: {
              accept: 'application/json, text/plain, */*',
            },
          });
          return {
            status: response.status,
            text: await response.text(),
          };
        })()
      `)
    },
  })

  const status = Number(result?.status)
  if (!Number.isFinite(status) || status < 200 || status >= 300) {
    throw new Error(`Bilibili request failed: ${status || 'unknown'}`)
  }

  const payload = JSON.parse(String(result?.text || '{}'))
  if (payload?.code !== undefined && payload.code !== 0) {
    throw new Error(`${payload?.message || payload?.msg || payload.code} (code=${payload.code})`)
  }
  return payload?.data || {}
}

const mapBilibiliVideo = (row, profile) => ({
  source: 'remote',
  site: 'bilibili',
  id: row?.bvid || row?.aid || row?.id || row?.arcurl,
  title: stripHtml(row?.title),
  url: normalizeUrl(row?.arcurl || (row?.bvid ? `/video/${row.bvid}` : ''), BILIBILI_ORIGIN),
  thumbnail: normalizeUrl(row?.pic || row?.cover || '', BILIBILI_ORIGIN),
  duration: parseDuration(row?.length || row?.duration),
  publish_date: row?.created ? new Date(Number(row.created) * 1000).toISOString() : null,
  uploader: profile.name,
  uploader_url: profile.url,
  uploader_avatar: profile.avatar,
  subscriptions: [profile],
  description: stripHtml(row?.description || ''),
})

const getBilibiliChannel = async ({ url, limit, page, fetchImpl, buildCookieHeader, loadDocumentHtml, profile }) => {
  const resultLimit = clampLimit(limit)
  const resultPage = clampPage(page)
  const channelUrl = normalizeChannelUrl(url)
  const mid = extractBilibiliMid(channelUrl)
  const cookie = await buildCookieHeader(BILIBILI_SPACE_ORIGIN)

  const profileUrl = new URL('https://api.bilibili.com/x/web-interface/card')
  profileUrl.searchParams.set('mid', mid)
  const profilePayload = await fetchBilibiliJson(fetchImpl, profileUrl.toString(), cookie)
  const card = profilePayload?.card || {}
  const channelProfile = {
    id: mid,
    type: 'CHANNEL',
    name: stripHtml(card?.name || profile?.name || ''),
    url: `https://space.bilibili.com/${mid}`,
    avatar: normalizeUrl(card?.face || profile?.avatar || '', BILIBILI_ORIGIN),
    description: stripHtml(card?.sign || ''),
    site: 'bilibili',
    is_nsfw: false,
  }

  const nav = await fetchBilibiliJson(fetchImpl, 'https://api.bilibili.com/x/web-interface/nav', cookie)
  const imgUrl = String(nav?.wbi_img?.img_url || '')
  const subUrl = String(nav?.wbi_img?.sub_url || '')
  const imgKey = imgUrl.split('/').pop()?.split('.')[0] || ''
  const subKey = subUrl.split('/').pop()?.split('.')[0] || ''
  if (!imgKey || !subKey) throw new Error('Bilibili WBI keys are missing')

  const baseParams = {
    mid,
    pn: String(resultPage),
    ps: String(resultLimit),
    order: 'pubdate',
    platform: 'web',
    web_location: BILIBILI_WEB_LOCATION_SPACE,
    order_avoided: 'true',
  }
  const videosPayload = await fetchBilibiliSpacePageJson({
    mid,
    page: resultPage,
    baseParams,
    imgKey,
    subKey,
    loadDocumentHtml,
  })
  const rows = Array.isArray(videosPayload?.list?.vlist) ? videosPayload.list.vlist : []
  const totalCount = Number(videosPayload?.page?.count)
  const hasTotalCount = Number.isFinite(totalCount) && totalCount >= 0

  return {
    profile: channelProfile,
    items: uniqueByUrl(rows.map((row) => mapBilibiliVideo(row, channelProfile))).filter((item) => item.title && item.url),
    page: resultPage,
    has_more: hasTotalCount ? resultPage * resultLimit < totalCount : rows.length >= resultLimit,
  }
}

const collectPornhubVideos = (html, profile) => {
  const blocks = html.match(/<li[^>]+class=["'][^"']*(?:pcVideoListItem|videoblock)[^"']*["'][\s\S]*?<\/li>/gi) || []
  return uniqueByUrl(blocks.map((block) => {
    const hrefMatch = block.match(/href=["']([^"']*view_video\.php\?viewkey=[^"']+)["']/i)
    const title = extractAttribute(block, 'data-title') || extractAttribute(block, 'title')
    const thumbnail = extractAttribute(block, 'data-mediumthumb') || extractAttribute(block, 'data-src') || extractAttribute(block, 'src')
    const durationMatch = block.match(/class=["'][^"']*duration[^"']*["'][^>]*>\s*([^<]+)/i)
    return {
      source: 'remote',
      site: 'pornhub',
      id: extractAttribute(block, 'data-video-vkey') || hrefMatch?.[1] || '',
      title: stripHtml(title),
      url: normalizeUrl(hrefMatch?.[1] || '', PORNHUB_ORIGIN),
      thumbnail: normalizeUrl(thumbnail, PORNHUB_ORIGIN),
      duration: parseDuration(durationMatch?.[1]),
      publish_date: null,
      uploader: profile.name,
      uploader_url: profile.url,
      uploader_avatar: profile.avatar,
      subscriptions: [profile],
      description: '',
    }
  })).filter((item) => item.title && item.url)
}

const getPornhubChannel = async ({ url, limit, page, fetchImpl, buildCookieHeader, profile }) => {
  const resultLimit = clampLimit(limit)
  const resultPage = clampPage(page)
  const channelUrl = normalizeChannelUrl(url)
  const targetUrl = new URL(channelUrl)
  targetUrl.searchParams.set('page', String(resultPage))
  const cookie = await buildCookieHeader(channelUrl)
  const html = await fetchText(fetchImpl, targetUrl.toString(), {
    headers: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      Referer: `${PORNHUB_ORIGIN}/`,
      ...(cookie ? { Cookie: cookie } : {}),
    },
  })
  const title = stripHtml(
    html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i)?.[1]
    || profile?.name
    || ''
  )
  const avatar = normalizeUrl(
    extractAttribute(html.match(/<img[^>]+class=["'][^"']*(?:avatar|profilePic)[^"']*["'][^>]*>/i)?.[0] || '', 'src')
    || profile?.avatar
    || '',
    PORNHUB_ORIGIN
  )
  const channelProfile = {
    id: profile?.id || null,
    type: 'CHANNEL',
    name: title,
    url: channelUrl,
    avatar,
    description: '',
    site: 'pornhub',
    is_nsfw: true,
  }
  const items = collectPornhubVideos(html, channelProfile)

  return {
    profile: channelProfile,
    items: items.slice(0, resultLimit),
    page: resultPage,
    has_more: items.length >= resultLimit,
  }
}

const collectYouPornVideos = (html, profile) => {
  const cardPattern = /<article\b[^>]*class=["'][^"']*\bvideo-box\b[^"']*["'][^>]*>[\s\S]*?<\/article>/gi
  const items = []
  let match
  while ((match = cardPattern.exec(html))) {
    const block = match[0]
    const href = extractAttribute(block, 'href')
    const titleLink = block.match(/<a[^>]+class=["'][^"']*video-title-text[^"']*["'][^>]*>([\s\S]*?)<\/a>/i)
    const image = block.match(/<img\b[^>]*>/i)?.[0] || ''
    const thumbnail = extractAttribute(image, 'data-src') || extractAttribute(image, 'data-poster') || extractAttribute(image, 'src')
    const durationMatch = block.match(/class=["'][^"']*duration[^"']*["'][^>]*>\s*([^<]+)/i)
    items.push({
      source: 'remote',
      site: 'youporn',
      id: href,
      title: stripHtml(extractAttribute(block, 'aria-label') || titleLink?.[1] || ''),
      url: normalizeUrl(href, YOUPORN_ORIGIN),
      thumbnail: normalizeUrl(thumbnail, YOUPORN_ORIGIN),
      duration: parseDuration(durationMatch?.[1]),
      publish_date: null,
      uploader: profile.name,
      uploader_url: profile.url,
      uploader_avatar: profile.avatar,
      subscriptions: [profile],
      description: '',
    })
  }
  return uniqueByUrl(items).filter((item) => item.title && item.url)
}

const getYouPornChannel = async ({ url, limit, page, fetchImpl, buildCookieHeader, profile }) => {
  const resultLimit = clampLimit(limit)
  const resultPage = clampPage(page)
  const channelUrl = normalizeChannelUrl(url)
  const targetUrl = new URL(channelUrl)
  targetUrl.searchParams.set('page', String(resultPage))
  const cookie = await buildCookieHeader(channelUrl)
  const html = await fetchText(fetchImpl, targetUrl.toString(), {
    headers: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      Referer: `${YOUPORN_ORIGIN}/`,
      ...(cookie ? { Cookie: cookie } : {}),
    },
  })
  const title = stripHtml(html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i)?.[1] || profile?.name || '')
  const avatar = normalizeUrl(
    extractAttribute(html.match(/<img[^>]+class=["'][^"']*(?:avatar|profile)[^"']*["'][^>]*>/i)?.[0] || '', 'src')
    || profile?.avatar
    || '',
    YOUPORN_ORIGIN
  )
  const channelProfile = {
    id: profile?.id || null,
    type: 'CHANNEL',
    name: title,
    url: channelUrl,
    avatar,
    description: '',
    site: 'youporn',
    is_nsfw: true,
  }
  const items = collectYouPornVideos(html, channelProfile)

  return {
    profile: channelProfile,
    items: items.slice(0, resultLimit),
    page: resultPage,
    has_more: items.length >= resultLimit,
  }
}

const CHANNEL_PROVIDERS = {
  bilibili: getBilibiliChannel,
  youtube: getYouTubeChannel,
  pornhub: getPornhubChannel,
  youporn: getYouPornChannel,
}

export const getRemoteChannel = async ({
  site,
  url,
  limit = 30,
  page = 1,
  cursor = null,
  profile = {},
  fetchImpl,
  buildCookieHeader,
  loadDocumentHtml,
}) => {
  if (typeof fetchImpl !== 'function') throw new Error('Channel fetch implementation is required')
  if (typeof buildCookieHeader !== 'function') throw new Error('Channel cookie resolver is required')

  const channelUrl = normalizeChannelUrl(url)
  const normalizedSite = normalizeSite(site, channelUrl)
  const provider = CHANNEL_PROVIDERS[normalizedSite]
  if (!provider) throw new Error(`Remote channel site is not supported: ${normalizedSite}`)

  const result = await provider({
    url: channelUrl,
    limit,
    page,
    cursor,
    profile,
    fetchImpl,
    buildCookieHeader,
    loadDocumentHtml,
  })

  return {
    site: normalizedSite,
    profile: result.profile,
    items: result.items,
    page: result.page,
    has_more: result.has_more,
    next_cursor: result.next_cursor || null,
  }
}
