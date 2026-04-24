import { createHash } from 'node:crypto'

const USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
const BILIBILI_REFERER = 'https://www.bilibili.com/'

const WBI_MIXIN_KEY_ENC_TAB = [
  46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
  33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
  61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
  36, 20, 34, 44, 52,
]

const buildHeaders = (cookie = '') => ({
  accept: 'application/json, text/plain, */*',
  'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
  'cache-control': 'no-cache',
  pragma: 'no-cache',
  referer: BILIBILI_REFERER,
  origin: BILIBILI_REFERER.replace(/\/$/, ''),
  'sec-ch-ua': '"Chromium";v="135", "Not-A.Brand";v="8"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"',
  'sec-fetch-dest': 'empty',
  'sec-fetch-mode': 'cors',
  'sec-fetch-site': 'same-site',
  'user-agent': USER_AGENT,
  ...(cookie ? { cookie } : {}),
})

const fetchBrowserJson = async (url, { cookie = '', params = null, timeoutMs = 25000, fetchImpl = null } = {}) => {
  const target = new URL(url)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== null && value !== undefined && value !== '') {
        target.searchParams.set(key, String(value))
      }
    }
  }

  const abortController = new AbortController()
  const timer = setTimeout(() => abortController.abort(), timeoutMs)
  try {
    const response = fetchImpl
      ? await fetchImpl(target.toString(), {
          method: 'GET',
          headers: buildHeaders(cookie),
          redirect: 'follow',
          timeoutMs,
        })
      : await fetch(target.toString(), {
          headers: buildHeaders(cookie),
          signal: abortController.signal,
        })
    const payload = typeof response.text === 'function'
      ? JSON.parse(await response.text())
      : await response.json()
    if (!response.ok) {
      throw new Error(`Bilibili request failed with HTTP ${response.status}`)
    }

    const code = payload?.code
    if (code !== undefined && code !== 0) {
      throw new Error(`${payload?.message || payload?.msg || code} (code=${code})`)
    }

    return payload?.data || payload || {}
  } finally {
    clearTimeout(timer)
  }
}

const extractPageIndex = (targetUrl) => {
  try {
    const url = new URL(targetUrl)
    const page = url.searchParams.get('p') || url.searchParams.get('page')
    const numericPage = Number.parseInt(page || '', 10)
    return Number.isFinite(numericPage) ? Math.max(numericPage - 1, 0) : 0
  } catch {
    return 0
  }
}

const extractVideoId = (targetUrl) => {
  const input = String(targetUrl || '')
  const bvidMatch = input.match(/(BV[0-9A-Za-z]{10,})/)
  if (bvidMatch?.[1]) {
    return { bvid: bvidMatch[1], aid: null }
  }

  const avMatch = input.match(/\/av(\d+)/i)
  if (avMatch?.[1]) {
    return { bvid: null, aid: Number.parseInt(avMatch[1], 10) }
  }

  try {
    const url = new URL(input)
    const queryBvid = url.searchParams.get('bvid')
    if (queryBvid && /^BV[0-9A-Za-z]{10,}$/.test(queryBvid)) {
      return { bvid: queryBvid, aid: null }
    }
    const queryAid = url.searchParams.get('aid') || url.searchParams.get('avid')
    const numericAid = Number.parseInt(queryAid || '', 10)
    if (Number.isFinite(numericAid)) {
      return { bvid: null, aid: numericAid }
    }
  } catch {
    // Ignore URL parse failures.
  }

  return { bvid: null, aid: null }
}

const getMixinKey = (value) => {
  return WBI_MIXIN_KEY_ENC_TAB
    .map((index) => value[index] || '')
    .join('')
    .slice(0, 32)
}

export async function resolveBilibiliApiPayload(targetUrl, { cookie = '', fetchImpl = null } = {}) {
  const pageIndex = extractPageIndex(targetUrl)
  const { bvid, aid } = extractVideoId(targetUrl)

  if (!bvid && !aid) {
    throw new Error('URL is not a supported Bilibili video link')
  }

  const infoParams = bvid ? { bvid } : { aid: String(aid) }
  const info = await fetchBrowserJson('https://api.bilibili.com/x/web-interface/view', {
    cookie,
    params: infoParams,
    fetchImpl,
  })
  const pages = Array.isArray(info?.pages) ? info.pages : []
  const pageInfo = pages[Math.min(pageIndex, Math.max(pages.length - 1, 0))] || null
  const cid = Number.parseInt(String(pageInfo?.cid || ''), 10)

  if (!Number.isFinite(cid)) {
    throw new Error('Failed to resolve Bilibili cid')
  }

  const nav = await fetchBrowserJson('https://api.bilibili.com/x/web-interface/nav', {
    cookie,
    timeoutMs: 15000,
    fetchImpl,
  })

  const imgUrl = String(nav?.wbi_img?.img_url || '')
  const subUrl = String(nav?.wbi_img?.sub_url || '')
  const imgKey = imgUrl.split('/').pop()?.split('.')[0] || ''
  const subKey = subUrl.split('/').pop()?.split('.')[0] || ''

  if (!imgKey || !subKey) {
    throw new Error('Bilibili WBI keys are missing')
  }

  const mixinKey = getMixinKey(`${imgKey}${subKey}`)
  const baseParams = {
    cid: String(cid),
    qn: '127',
    fnver: '0',
    fnval: '4048',
    fourk: '1',
    ...(bvid ? { bvid } : { aid: String(aid) }),
    wts: String(Math.round(Date.now() / 1000)),
  }

  const sortedEntries = Object.entries(baseParams)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => [
      key,
      String(value).replace(/[!'()*]/g, ''),
    ])

  const query = new URLSearchParams(sortedEntries).toString()
  const w_rid = createHash('md5').update(`${query}${mixinKey}`).digest('hex')

  const playData = await fetchBrowserJson('https://api.bilibili.com/x/player/wbi/playurl', {
    cookie,
    params: {
      ...Object.fromEntries(sortedEntries),
      w_rid,
    },
    fetchImpl,
  })

  return {
    info,
    context: {
      url: targetUrl,
      pageIndex,
      bvid: info?.bvid || bvid || null,
      aid: info?.aid || aid || null,
      cid,
    },
    playData,
  }
}
