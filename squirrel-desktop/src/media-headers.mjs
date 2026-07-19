import { session } from 'electron'
import { buildCookieHeaderForUrl } from './site-login.mjs'
import { mergeCookieHeaders } from './cookie-header.mjs'
import {
  desktopChromeUserAgent,
  androidMobileChromeUserAgent,
} from './constants.mjs'

const MEDIA_HEADER_RULES = [
  {
    hosts: ['bilivideo.com', 'bilivideo.cn', 'hdslb.com', 'acgvideo.com'],
    headers: {
      Referer: 'https://www.bilibili.com/',
      Origin: 'https://www.bilibili.com',
      'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
      'User-Agent': desktopChromeUserAgent,
    },
  },
  {
    hosts: ['googlevideo.com', 'gvt1.com', 'ytimg.com'],
    headers: {
      Referer: 'https://m.youtube.com/',
      Origin: 'https://m.youtube.com',
      'User-Agent': androidMobileChromeUserAgent,
    },
  },
  {
    hosts: ['youtube.com'],
    headers: {
      Referer: 'https://www.youtube.com/',
      Origin: 'https://www.youtube.com',
      'User-Agent': desktopChromeUserAgent,
    },
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
]

const RELAXED_RESPONSE_HEADER_NAMES = new Set([
  'cross-origin-resource-policy',
  'cross-origin-embedder-policy',
  'cross-origin-opener-policy',
])

const hostMatchesAnyRule = (hostname, hosts) => {
  return hosts.some((host) => hostname === host || hostname.endsWith(`.${host}`))
}

const matchMediaHeaderRule = (targetUrl) => {
  try {
    const hostname = new URL(targetUrl).hostname.toLowerCase()
    return MEDIA_HEADER_RULES.find((rule) => {
      return hostMatchesAnyRule(hostname, rule.hosts)
    }) || null
  } catch (err) {
    console.debug('[squirrel-desktop] matchMediaHeaderRule error', err)
    return null
  }
}

const shouldRelaxCrossOriginResponseHeaders = (targetUrl) => {
  try {
    const hostname = new URL(targetUrl).hostname.toLowerCase()
    return hostMatchesAnyRule(hostname, RELAXED_CROSS_ORIGIN_HOSTS)
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

    const requestHeaders = {
      ...details.requestHeaders,
      ...rule.headers,
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
