/**
 * Bridge for exporting Electron session cookies to the (possibly REMOTE)
 * Squirrel backend. The backend upload endpoint (POST /api/site-cookies/{site})
 * accepts a multipart text file in Netscape cookies.txt format, domain-filters
 * the lines, and writes them to config/site_cookies/{site}.txt on the server.
 *
 * This module is deliberately pure (no Electron imports) so the serialization
 * and payload construction are unit-testable under plain `node --test`.
 */

export const NETSCAPE_HEADER = '# Netscape HTTP Cookie File'

const expiresEpoch = (cookie) => {
  const raw = Number(cookie?.expirationDate)
  if (!Number.isFinite(raw) || raw <= 0) return 0
  return Math.floor(raw)
}

/**
 * Serialize Electron session cookie objects into Netscape cookies.txt lines.
 * Field order matches what cookielib.MozillaCookieJar expects:
 *   domain  includeSubdomains  path  secure  expires(epoch)  name  value
 * The leading dot of domain-scoped cookies is KEPT because the jar asserts
 * includeSubdomains == domain.startsWith('.') (cookiejar.py:2051). HttpOnly
 * cookies get the `#HttpOnly_` domain prefix, which the backend upload parser
 * (site_cookies_single_upload.py -> normalize_cookie_domain) strips along with
 * the leading dot before domain-matching.
 */
export const serializeCookiesToNetscape = (cookies) => {
  const lines = [NETSCAPE_HEADER]
  for (const cookie of cookies || []) {
    if (!cookie?.name || !cookie?.value) continue
    const rawDomain = String(cookie.domain || '').trim().replace(/^#HttpOnly_/i, '')
    if (!rawDomain) continue

    const subdomains = rawDomain.startsWith('.') ? 'TRUE' : 'FALSE'
    const path = cookie.path || '/'
    const secure = cookie.secure ? 'TRUE' : 'FALSE'
    const expires = String(expiresEpoch(cookie))
    const prefix = cookie.httpOnly ? '#HttpOnly_' : ''

    lines.push([`${prefix}${rawDomain}`, subdomains, path, secure, expires, cookie.name, cookie.value].join('\t'))
  }
  return lines.join('\n')
}

export const buildCookieUploadPayload = (siteName, cookies) => {
  const normalizedSite = String(siteName || '').trim().toLowerCase()
  const text = serializeCookiesToNetscape(cookies)
  return {
    fileName: `${normalizedSite || 'site'}.txt`,
    text,
    count: (cookies || []).filter((cookie) => cookie?.name && cookie?.value).length,
  }
}

const withTimeout = (fetchImpl, timeoutMs) => {
  return async (url, options = {}) => {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    try {
      return await fetchImpl(url, { ...options, signal: controller.signal })
    } finally {
      clearTimeout(timer)
    }
  }
}

/**
 * Push cookies to the backend upload endpoint.
 * `fetchImpl` is injected so tests can mock it; in production it is
 * `session.defaultSession.fetch`, which inherits the backend JWT cookie via the
 * media-headers webRequest hook (isConfiguredBackendApiUrl) — no manual auth.
 * Never writes local files: the backend may be a remote server.
 */
export const exportSiteCookiesToBackend = async ({ siteName, cookies, serverUrl, fetchImpl, timeoutMs = 25000 }) => {
  const normalizedSite = String(siteName || '').trim().toLowerCase()
  const origin = String(serverUrl || '').trim().replace(/\/+$/, '')
  if (!normalizedSite || !origin) {
    return { ok: false, reason: 'no-server-or-site', message: '未配置服务器地址' }
  }

  const payload = buildCookieUploadPayload(normalizedSite, cookies)
  if (payload.count === 0) {
    return { ok: false, reason: 'no-cookies', message: '未发现可导出的站点 Cookie' }
  }

  const form = new FormData()
  form.append('file', new Blob([payload.text], { type: 'text/plain' }), payload.fileName)

  const request = typeof fetchImpl === 'function' ? withTimeout(fetchImpl, timeoutMs) : fetchImpl
  try {
    const response = await request(`${origin}/api/site-cookies/${normalizedSite}`, {
      method: 'POST',
      body: form,
    })
    let json = null
    try {
      json = await response.json()
    } catch {
      // non-JSON body — keep null
    }

    if (!response.ok) {
      return {
        ok: false,
        reason: 'http-error',
        status: response.status,
        message: json?.msg || `HTTP ${response.status}`,
      }
    }
    if (json && json.code !== 0) {
      return { ok: false, reason: 'api-error', message: json.msg || 'cookies 上传失败' }
    }

    return {
      ok: true,
      message: json?.msg || 'cookies exported',
      data: json?.data || null,
      count: payload.count,
    }
  } catch (error) {
    return { ok: false, reason: 'network-error', message: error?.message || String(error) }
  }
}
