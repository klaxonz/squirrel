export const normalizeTargetUrl = (targetUrl) => {
  const value = String(targetUrl || '').trim()
  if (!value) {
    return ''
  }

  try {
    return new URL(value).toString()
  } catch {
    console.debug('[squirrel-desktop] cookie-header: normalizeTargetUrl failed to parse', value)
    return ''
  }
}

export const isBilibiliCookieTarget = (targetUrl) => {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    return false
  }

  try {
    const hostname = new URL(normalizedUrl).hostname.toLowerCase()
    return hostname === 'bilibili.com'
      || hostname.endsWith('.bilibili.com')
      || hostname === 'b23.tv'
      || hostname.endsWith('.bilivideo.com')
      || hostname.endsWith('.bilivideo.cn')
      || hostname.endsWith('.hdslb.com')
      || hostname.endsWith('.acgvideo.com')
  } catch {
    console.debug('[squirrel-desktop] cookie-header: isBilibiliCookieTarget URL parse failed', normalizedUrl)
    return false
  }
}

export const mergeCookieHeaders = (...cookieHeaders) => {
  const cookieMap = new Map()

  for (const header of cookieHeaders) {
    const normalizedHeader = String(header || '').trim()
    if (!normalizedHeader) {
      continue
    }

    for (const segment of normalizedHeader.split(';')) {
      const pair = segment.trim()
      if (!pair) {
        continue
      }

      const equalsIndex = pair.indexOf('=')
      if (equalsIndex <= 0) {
        continue
      }

      const name = pair.slice(0, equalsIndex).trim()
      const value = pair.slice(equalsIndex + 1).trim()
      if (!name) {
        continue
      }

      cookieMap.set(name, value)
    }
  }

  return Array.from(cookieMap.entries())
    .map(([name, value]) => `${name}=${value}`)
    .join('; ')
}
