import { app, session } from 'electron'
import { buildCookieHeaderForUrl } from './site-login.mjs'
import { mergeCookieHeaders } from './cookie-header.mjs'
import { attachBackendSessionCookies, isConfiguredBackendApiUrl } from './backend-auth-headers.mjs'
import { getConfiguredServerUrl } from './ipc-server-config.mjs'
import {
  APP_NAME,
  desktopChromeUserAgent,
  stripElectronFromUserAgent,
} from './constants.mjs'

const BILIBILI_MEDIA_HEADERS = {
  Referer: 'https://www.bilibili.com/',
  Origin: 'https://www.bilibili.com',
  'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
  'User-Agent': desktopChromeUserAgent,
  // CDN responses carry last-modified without cache-control, so Chromium
  // heuristic-caches signed media ranges; the player then measures ~0 network
  // time and ABR/session quality collapses. Media URLs are ephemeral and
  // signed — never store them.
  'Cache-Control': 'no-store',
  Pragma: 'no-cache',
}

/**
 * YouTube media — FreeTube-aligned (src/main/index.js onBeforeSendHeaders):
 *  - googlevideo /videoplayback: Referer + Origin youtube.com
 *  - strip Content-Type (YouTube itself does not send it on media)
 *  - never attach site cookies to signature-bound googlevideo URLs
 *  - force Chrome UA (no Electron token) — session default alone is not enough
 *    if a request plugin reintroduces Electron in User-Agent
 * Do NOT rewrite UA per client, re-map Range across redirects, or proxy.
 */
const YOUTUBE_MEDIA_HEADERS = {
  Referer: 'https://www.youtube.com/',
  Origin: 'https://www.youtube.com',
  'User-Agent': desktopChromeUserAgent,
  'Cache-Control': 'no-store',
  Pragma: 'no-cache',
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

/**
 * Chromium may keep both `Origin` and `origin` (and same for Referer/UA).
 * Spreading rule headers only overwrites one casing — the renderer page
 * origin (dev Vite loopback) can still win and googlevideo returns 403.
 * Always delete both casings before applying FreeTube media headers.
 */
const deleteHeaderCaseInsensitive = (headers, name) => {
  const target = String(name || '').toLowerCase()
  for (const key of Object.keys(headers || {})) {
    if (String(key).toLowerCase() === target) {
      delete headers[key]
    }
  }
}

const applyRequestHeaders = (details, rule) => {
  const requestHeaders = {
    ...details.requestHeaders,
  }

  // Drop any prior Origin/Referer/User-Agent (both casings) before FreeTube values.
  for (const name of Object.keys(rule.headers || {})) {
    deleteHeaderCaseInsensitive(requestHeaders, name)
  }
  Object.assign(requestHeaders, rule.headers)

  if (rule.stripCookies) {
    deleteHeaderCaseInsensitive(requestHeaders, 'Cookie')
  }

  // FreeTube: YouTube does not send Content-Type on media segment requests.
  if (rule.stripContentTypeOnVideoplayback && isYouTubeVideoplaybackUrl(details.url)) {
    deleteHeaderCaseInsensitive(requestHeaders, 'Content-Type')
  }

  return requestHeaders
}

/**
 * FreeTube: session.defaultSession.setUserAgent(strip Electron / product).
 * Must run before media requests; otherwise googlevideo sees Electron/x.y.
 * Also set app.userAgentFallback so new webContents inherit Chrome UA.
 */
export const installDesktopSessionUserAgent = () => {
  const ses = session.defaultSession
  const raw = typeof ses.getUserAgent === 'function' ? ses.getUserAgent() : desktopChromeUserAgent
  const fixed = stripElectronFromUserAgent(raw, APP_NAME) || desktopChromeUserAgent
  if (typeof ses.setUserAgent === 'function') {
    ses.setUserAgent(fixed)
  }
  // Electron: fallback UA for webContents that do not set their own.
  try {
    if (app && typeof app.userAgentFallback === 'string') {
      app.userAgentFallback = fixed
    }
  } catch {
    // app may be unavailable in unit-test import graphs
  }
  return fixed
}

export const installDesktopMediaHeaders = () => {
  const ses = session.defaultSession
  // Session-wide Chrome UA (FreeTube). Also force UA on YouTube media rules below.
  installDesktopSessionUserAgent()

  // Electron webRequest listeners do NOT return an unsubscribe function.
  // Passing `null` as the listener removes the previous handler (see Electron docs).
  ses.webRequest.onBeforeSendHeaders((details, callback) => {
    const rule = matchMediaHeaderRule(details.url)
    const requestHeaders = rule
      ? applyRequestHeaders(details, rule)
      : { ...details.requestHeaders }

    if (rule?.attachCookies === false || rule?.stripCookies) {
      callback({ requestHeaders })
      return
    }

    const isBackendRequest = isConfiguredBackendApiUrl(details.url, getConfiguredServerUrl())
    const shouldAttachSiteCookies = Boolean(rule?.attachCookies)
    if (!isBackendRequest && !shouldAttachSiteCookies) {
      callback({ requestHeaders })
      return
    }

    void buildCookieHeaderForUrl(details.url).then((desktopCookieHeader) => {
      if (isBackendRequest) {
        callback({
          requestHeaders: attachBackendSessionCookies(requestHeaders, desktopCookieHeader),
        })
        return
      }

      const cookieHeader = mergeCookieHeaders(
        requestHeaders.Cookie,
        requestHeaders.cookie,
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
