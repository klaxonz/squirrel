import { session } from 'electron'
import { buildCookieHeaderForUrl } from './site-login.mjs'
import { mergeCookieHeaders } from './cookie-header.mjs'
import {
  desktopChromeUserAgent,
} from './constants.mjs'

const BILIBILI_MEDIA_HEADERS = {
  Referer: 'https://www.bilibili.com/',
  Origin: 'https://www.bilibili.com',
  'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
  'User-Agent': desktopChromeUserAgent,
}

/**
 * YouTube media — FreeTube-aligned (src/main/index.js onBeforeSendHeaders):
 *  - googlevideo /videoplayback: Referer + Origin youtube.com
 *  - strip Content-Type (YouTube itself does not send it on media)
 *  - never attach site cookies to signature-bound googlevideo URLs
 * Do NOT rewrite UA per client, re-map Range across redirects, or proxy.
 */
const YOUTUBE_MEDIA_HEADERS = {
  Referer: 'https://www.youtube.com/',
  Origin: 'https://www.youtube.com',
}

const MEDIA_HEADER_RULES = [
  {
    hosts: ['bilivideo.com', 'bilivideo.cn', 'hdslb.com', 'acgvideo.com', 'mountaintoys.cn'],
    headers: BILIBILI_MEDIA_HEADERS,
    attachCookies: true,
  },
  {
    hosts: ['googlevideo.com', 'gvt1.com', 'ytimg.com'],
    headers: YOUTUBE_MEDIA_HEADERS,
    attachCookies: false,
    stripCookies: true,
    // FreeTube only strips Content-Type on googlevideo videoplayback.
    stripContentTypeOnVideoplayback: true,
  },
  {
    hosts: ['youtube.com'],
    headers: {
      Referer: 'https://www.youtube.com/',
      Origin: 'https://www.youtube.com',
    },
    attachCookies: true,
  },
]

const RELAXED_CROSS_ORIGIN_HOSTS = [
  'youtube.com',
  'googlevideo.com',
  'gvt1.com',
  'ytimg.com',
  'bilibili.com',
  'b23.tv',
  'bilivideo.com',
  'bilivideo.cn',
  'hdslb.com',
  'acgvideo.com',
  'mountaintoys.cn',
]

/**
 * Bilibili playurl often serves media from third-party edge hostnames
 * (not *.bilivideo.*) while keeping bilibili path/query signatures. Those
 * edges still require bilibili Referer/Origin or they return 403.
 */
export const isBilibiliEdgeMediaUrl = (targetUrl) => {
  const value = String(targetUrl || '')
  if (!value) return false
  try {
    const url = new URL(value)
    if (/\/upgcxcode\//i.test(url.pathname)) return true
    if (url.searchParams.get('bvc') === 'vod') return true
    if (url.searchParams.has('upsig') && url.searchParams.has('uparams')) return true
    return false
  } catch {
    return /\/upgcxcode\//i.test(value) || /[?&]bvc=vod\b/i.test(value)
  }
}

const RELAXED_RESPONSE_HEADER_NAMES = new Set([
  'cross-origin-resource-policy',
  'cross-origin-embedder-policy',
  'cross-origin-opener-policy',
])

const hostMatchesAnyRule = (hostname, hosts) => {
  return hosts.some((host) => hostname === host || hostname.endsWith(`.${host}`))
}

export const matchMediaHeaderRule = (targetUrl) => {
  try {
    const hostname = new URL(targetUrl).hostname.toLowerCase()
    const hostRule = MEDIA_HEADER_RULES.find((rule) => {
      return hostMatchesAnyRule(hostname, rule.hosts)
    })
    if (hostRule) return hostRule
    if (isBilibiliEdgeMediaUrl(targetUrl)) {
      return { hosts: [], headers: BILIBILI_MEDIA_HEADERS, attachCookies: true }
    }
    return null
  } catch (err) {
    console.debug('[squirrel-desktop] matchMediaHeaderRule error', err)
    return null
  }
}

const shouldRelaxCrossOriginResponseHeaders = (targetUrl) => {
  try {
    const hostname = new URL(targetUrl).hostname.toLowerCase()
    if (hostMatchesAnyRule(hostname, RELAXED_CROSS_ORIGIN_HOSTS)) return true
    return isBilibiliEdgeMediaUrl(targetUrl)
  } catch (err) {
    console.debug('[squirrel-desktop] shouldRelaxCrossOriginResponseHeaders error', err)
    return false
  }
}

const stripRelaxedResponseHeaders = (responseHeaders) => {
  const filteredHeaders = {}
  for (const [name, value] of Object.entries(responseHeaders || {})) {
    if (RELAXED_RESPONSE_HEADER_NAMES.has(String(name).toLowerCase())) {
      continue
    }
    filteredHeaders[name] = value
  }
  return filteredHeaders
}

const isYouTubeVideoplaybackUrl = (targetUrl) => {
  try {
    const url = new URL(targetUrl)
    return (
      (url.hostname.endsWith('.googlevideo.com') || url.hostname === 'googlevideo.com')
      && url.pathname === '/videoplayback'
    )
  } catch {
    return false
  }
}

const applyRequestHeaders = (details, rule) => {
  const requestHeaders = {
    ...details.requestHeaders,
    ...rule.headers,
  }

  if (rule.stripCookies) {
    delete requestHeaders.Cookie
    delete requestHeaders.cookie
  }

  // FreeTube: YouTube does not send Content-Type on media segment requests.
  if (rule.stripContentTypeOnVideoplayback && isYouTubeVideoplaybackUrl(details.url)) {
    delete requestHeaders['Content-Type']
    delete requestHeaders['content-type']
  }

  return requestHeaders
}

export const installDesktopMediaHeaders = () => {
  const ses = session.defaultSession

  // Electron webRequest listeners do NOT return an unsubscribe function.
  // Passing `null` as the listener removes the previous handler (see Electron docs).
  ses.webRequest.onBeforeSendHeaders((details, callback) => {
    const rule = matchMediaHeaderRule(details.url)
    if (!rule) {
      callback({ requestHeaders: details.requestHeaders })
      return
    }

    const requestHeaders = applyRequestHeaders(details, rule)

    if (rule.attachCookies === false || rule.stripCookies) {
      callback({ requestHeaders })
      return
    }

    void buildCookieHeaderForUrl(details.url).then((desktopCookieHeader) => {
      const cookieHeader = mergeCookieHeaders(
        details.requestHeaders?.Cookie,
        details.requestHeaders?.cookie,
        desktopCookieHeader,
      )
      if (cookieHeader) {
        requestHeaders.Cookie = cookieHeader
        delete requestHeaders.cookie
      }

      callback({ requestHeaders })
    }).catch((err) => {
      console.debug('[squirrel-desktop] buildCookieHeaderForUrl error', err)
      callback({ requestHeaders })
    })
  })

  ses.webRequest.onHeadersReceived((details, callback) => {
    if (!shouldRelaxCrossOriginResponseHeaders(details.url)) {
      callback({ responseHeaders: details.responseHeaders })
      return
    }

    callback({
      responseHeaders: stripRelaxedResponseHeaders(details.responseHeaders),
    })
  })

  return () => {
    try {
      ses.webRequest.onBeforeSendHeaders(null)
      ses.webRequest.onHeadersReceived(null)
    } catch (err) {
      console.debug('[squirrel-desktop] media-headers cleanup error', err)
    }
  }
}
