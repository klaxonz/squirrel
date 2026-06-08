import { session } from 'electron'
import { buildCookieHeaderForUrl } from './site-login.mjs'
import { mergeCookieHeaders } from './cookie-header.mjs'
import {
  desktopChromeUserAgent,
  desktopMacChromeUserAgent,
  androidMobileChromeUserAgent,
  desktopChromeClientHints,
  desktopChromeAcceptLanguage,
} from './constants.mjs'

const MEDIA_HEADER_RULES = [
  {
    hosts: ['javdb.com'],
    headers: {
      'Accept-Language': desktopChromeAcceptLanguage,
      'User-Agent': desktopChromeUserAgent,
      ...desktopChromeClientHints,
    },
  },
  {
    hosts: ['missav.ai'],
    headers: {
      'Accept-Language': desktopChromeAcceptLanguage,
      'User-Agent': desktopChromeUserAgent,
      ...desktopChromeClientHints,
    },
  },
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
  {
    hosts: ['pornhub.com', 'phncdn.com'],
    headers: {
      Referer: 'https://www.pornhub.com/',
      Origin: 'https://www.pornhub.com',
      'User-Agent': desktopMacChromeUserAgent,
    },
  },
  {
    hosts: ['youporn.com', 'ypncdn.com'],
    headers: {
      Referer: 'https://www.youporn.com/',
      Origin: 'https://www.youporn.com',
      'User-Agent': desktopMacChromeUserAgent,
    },
  },
  {
    hosts: ['surrit.com'],
    headers: {
      Referer: 'https://missav.ai/',
      Origin: 'https://missav.ai',
      'User-Agent': desktopMacChromeUserAgent,
    },
  },
  {
    hosts: ['jdbstatic.com'],
    headers: {
      Referer: 'https://javdb.com/',
      Origin: 'https://javdb.com',
      'User-Agent': desktopChromeUserAgent,
      ...desktopChromeClientHints,
    },
  },
]

const RELAXED_CROSS_ORIGIN_HOSTS = [
  'javdb.com',
  'surrit.com',
  'jdbstatic.com',
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
  'pornhub.com',
  'phncdn.com',
  'youporn.com',
  'ypncdn.com',
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
  const removeBeforeSend = session.defaultSession.webRequest.onBeforeSendHeaders((details, callback) => {
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

  const removeHeadersReceived = session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    // Strip X-Frame-Options and CSP headers for subFrame requests (iframes) to allow previewing inside the app
    if (details.resourceType === 'subFrame') {
      const responseHeaders = { ...details.responseHeaders }
      for (const key of Object.keys(responseHeaders)) {
        const lowerKey = key.toLowerCase()
        if (
          lowerKey === 'x-frame-options' ||
          lowerKey === 'content-security-policy' ||
          lowerKey === 'content-security-policy-report-only'
        ) {
          delete responseHeaders[key]
        }
      }
      callback({ responseHeaders })
      return
    }

    if (!shouldRelaxCrossOriginResponseHeaders(details.url)) {
      callback({ responseHeaders: details.responseHeaders })
      return
    }

    callback({
      responseHeaders: stripRelaxedResponseHeaders(details.responseHeaders),
    })
  })

  return () => {
    removeBeforeSend()
    removeHeadersReceived()
  }
}
