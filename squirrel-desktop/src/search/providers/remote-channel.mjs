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
import {
  collectVideoRenderers,
  collectLockupViewModels,
  findWatchVideoId,
  findContinuationToken,
  extractApiKey,
  extractContext,
  buildCursor,
  buildContinuationContext,
  extractLockupDuration,
  extractLockupPublishedText,
  pickLockupThumbnail,
  YOUTUBE_ORIGIN,
} from './youtube-shared.mjs'

import { signBilibiliWbiParams } from '../../shared/bilibili-sign.mjs'
import { desktopChromeUserAgent } from '../../constants.mjs'

const BILIBILI_ORIGIN = 'https://www.bilibili.com'
const BILIBILI_SPACE_ORIGIN = 'https://space.bilibili.com'
const DESKTOP_USER_AGENT = desktopChromeUserAgent
const BILIBILI_WEB_LOCATION_SPACE = '1550101'

const SITE_ALIASES = {
  'bilibili.com': 'bilibili',
  'b23.tv': 'bilibili',
  'youtube.com': 'youtube',
  'youtu.be': 'youtube',
}

const normalizeSite = (site, targetUrl) => {
  const rawSite = String(site || '').trim().toLowerCase()
  if (rawSite && rawSite !== 'all') return SITE_ALIASES[rawSite.replace(/^www\./, '')] || rawSite

  const hostname = new URL(targetUrl).hostname.toLowerCase().replace(/^www\./, '')
  return SITE_ALIASES[hostname] || hostname
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

const normalizeChannelUrl = (value) => {
  const url = normalizeUrl(value, YOUTUBE_ORIGIN)
  if (!url) throw new Error('Remote channel URL is required')
  return url
}

const buildYouTubeVideosUrl = (channelUrl) => {
  const url = new URL(channelUrl)
  if (!url.pathname.endsWith('/videos')) {
    url.pathname = `${url.pathname.replace(/\/$/, '')}/videos`
  }
  return url.toString()
}

const buildYouTubeChannelUrl = (url, profile = {}) => {
  const profileId = String(profile?.id || '').trim()
  if (profileId.startsWith('UC')) return `${YOUTUBE_ORIGIN}/channel/${encodeURIComponent(profileId)}`
  return normalizeChannelUrl(url)
}

const parseLooseCount = (value) => {
  if (value == null) return null
  if (typeof value === 'number' && Number.isFinite(value)) return Math.max(0, Math.floor(value))
  const text = String(value).trim()
  if (!text) return null
  // "1.2M subscribers", "12,345", "123万"
  const compact = text.replace(/,/g, '').toLowerCase()
  const wan = compact.match(/([\d.]+)\s*万/)
  if (wan) return Math.floor(Number(wan[1]) * 10_000)
  const yi = compact.match(/([\d.]+)\s*亿/)
  if (yi) return Math.floor(Number(yi[1]) * 100_000_000)
  const m = compact.match(/([\d.]+)\s*m\b/)
  if (m) return Math.floor(Number(m[1]) * 1_000_000)
  const k = compact.match(/([\d.]+)\s*k\b/)
  if (k) return Math.floor(Number(k[1]) * 1_000)
  const plain = compact.match(/([\d.]+)/)
  if (!plain) return null
  const n = Number(plain[1])
  return Number.isFinite(n) ? Math.floor(n) : null
}

const extractYouTubeProfile = (initialData, channelUrl, providedProfile = {}) => {
  const metadata = initialData?.metadata?.channelMetadataRenderer || {}
  const header = initialData?.header?.pageHeaderRenderer || initialData?.header?.c4TabbedHeaderRenderer || {}
  const avatar = pickThumbnail(
    header?.image?.decoratedAvatarViewModel?.avatar?.avatarViewModel?.image?.sources
    || header?.avatar?.thumbnails
    || metadata?.avatar?.thumbnails
  )
  const banner = pickThumbnail(
    header?.banner?.thumbnails
    || header?.content?.pageHeaderViewModel?.banner?.imageBannerViewModel?.image?.sources
    || header?.image?.contentImageViewModel?.image?.sources
  )
  const subscriberText = pickText(header?.subscriberCountText)
    || pickText(header?.content?.pageHeaderViewModel?.metadata?.contentMetadataViewModel?.metadataRows?.[1]?.metadataParts?.[0]?.text)
    || ''
  const videoCountText = pickText(header?.videosCountText)
    || pickText(header?.content?.pageHeaderViewModel?.metadata?.contentMetadataViewModel?.metadataRows?.[1]?.metadataParts?.[1]?.text)
    || ''
  const name = metadata?.title || pickText(header?.title) || providedProfile.name || ''
  return {
    id: metadata?.externalId || providedProfile.id || null,
    type: 'CHANNEL',
    name,
    url: channelUrl,
    avatar: avatar || providedProfile.avatar || '',
    banner: banner || providedProfile.banner || null,
    description: metadata?.description || '',
    subscriber_count: parseLooseCount(subscriberText),
    video_count: parseLooseCount(videoCountText),
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

const mapYouTubeLockup = (lockup, profile) => {
  const videoId = findWatchVideoId(lockup)
  return {
    source: 'remote',
    site: 'youtube',
    id: videoId,
    title: lockup?.metadata?.lockupMetadataViewModel?.title?.content || '',
    url: videoId ? `${YOUTUBE_ORIGIN}/watch?v=${encodeURIComponent(videoId)}` : '',
    thumbnail: pickLockupThumbnail(lockup),
    duration: extractLockupDuration(lockup),
    publish_date: null,
    published_text: extractLockupPublishedText(lockup),
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
  collectVideoRenderers(payload, renderers)
  collectLockupViewModels(payload, lockups)
  return uniqueByUrl([
    ...renderers.map((renderer) => mapYouTubeVideo(renderer, profile)),
    ...lockups.map((lockup) => mapYouTubeLockup(lockup, profile)),
  ]).filter((item) => item.id && item.title && item.url)
}

const fetchYouTubeContinuation = async ({ cursor, fetchImpl, buildCookieHeader }) => {
  const continuation = String(cursor?.continuation || '').trim()
  const apiKey = String(cursor?.api_key || '').trim()
  if (!continuation || !apiKey) throw new Error('YouTube continuation cursor is missing')

  const cookie = await buildCookieHeader(YOUTUBE_ORIGIN)
  const context = buildContinuationContext(cursor)
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
    body: JSON.stringify({ context, continuation }),
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
    const continuation = findContinuationToken(payload)
    const items = mapYouTubeItems(payload, channelProfile)

    return {
      profile: channelProfile,
      items: items.slice(0, resultLimit),
      page: resultPage,
      has_more: !!continuation,
      next_cursor: continuation ? { ...cursor, continuation } : null,
    }
  }

  const channelUrl = buildYouTubeChannelUrl(url, profile)
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
  const apiKey = extractApiKey(html)
  const context = extractContext(html)
  const channelProfile = extractYouTubeProfile(initialData, channelUrl, profile)
  const continuation = findContinuationToken(initialData)
  const items = mapYouTubeItems(initialData, channelProfile)

  return {
    profile: channelProfile,
    items: items.slice(0, resultLimit),
    page: 1,
    has_more: !!continuation,
    next_cursor: buildCursor(continuation, apiKey, context),
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
  const pageValue = await readBilibiliSpacePageValue({
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

  const status = Number(pageValue?.status)
  if (!Number.isFinite(status) || status < 200 || status >= 300) {
    throw new Error(`Bilibili request failed: ${status || 'unknown'}`)
  }

  const payload = JSON.parse(String(pageValue?.text || '{}'))
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
    banner: normalizeUrl(card?.top_photo || card?.space?.top_photo || profile?.banner || '', BILIBILI_ORIGIN) || null,
    subscriber_count: parseLooseCount(card?.fans ?? profilePayload?.follower ?? profilePayload?.card?.fans),
    video_count: parseLooseCount(card?.archive_count ?? profilePayload?.archive_count),
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
  if (hasTotalCount && (channelProfile.video_count == null || channelProfile.video_count <= 0)) {
    channelProfile.video_count = totalCount
  }

  return {
    profile: channelProfile,
    items: uniqueByUrl(rows.map((row) => mapBilibiliVideo(row, channelProfile))).filter((item) => item.title && item.url),
    page: resultPage,
    has_more: hasTotalCount ? resultPage * resultLimit < totalCount : rows.length >= resultLimit,
  }
}

const CHANNEL_PROVIDERS = {
  bilibili: getBilibiliChannel,
  youtube: getYouTubeChannel,
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

  const providerResult = await provider({
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
    profile: providerResult.profile,
    items: providerResult.items,
    page: providerResult.page,
    has_more: providerResult.has_more,
    next_cursor: providerResult.next_cursor || null,
  }
}
