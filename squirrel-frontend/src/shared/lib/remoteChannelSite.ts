/** Resolve a channel/profile URL to a known remote site key for desktop browse. */

export function resolveRemoteChannelSite(url: string): string {
  let parsedUrl: URL
  try {
    parsedUrl = new URL(url)
  } catch {
    return ''
  }

  const hostname = parsedUrl.hostname.toLowerCase().replace(/^www\./, '')
  const pathname = parsedUrl.pathname

  if (hostname === 'space.bilibili.com' && /^\/\d+/i.test(pathname)) return 'bilibili'
  if (hostname === 'youtube.com' && /^\/(?:@[^/]+|channel\/[^/]+|c\/[^/]+|user\/[^/]+)/i.test(pathname)) {
    return 'youtube'
  }
  if (hostname === 'javdb.com' && /^\/actors?\//i.test(pathname)) return 'javdb'
  if (hostname === 'pornhub.com' && /^\/(?:users?|channels?|model|pornstar)\//i.test(pathname)) {
    return 'pornhub'
  }
  if (hostname === 'youporn.com' && /^\/(?:channel|amateur|pornstar|model)\//i.test(pathname)) {
    return 'youporn'
  }

  return ''
}
