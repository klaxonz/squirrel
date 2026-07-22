import { mergeCookieHeaders } from './cookie-header.mjs'

const deleteHeaderCaseInsensitive = (headers, name) => {
  const normalizedName = String(name || '').toLowerCase()
  for (const key of Object.keys(headers || {})) {
    if (key.toLowerCase() === normalizedName) delete headers[key]
  }
}

const readHeaderCaseInsensitive = (headers, name) => {
  const normalizedName = String(name || '').toLowerCase()
  const key = Object.keys(headers || {}).find((candidate) => candidate.toLowerCase() === normalizedName)
  return key ? headers[key] : ''
}

/** Only the configured backend's API surface may receive its session cookies. */
export const isConfiguredBackendApiUrl = (targetUrl, configuredServerUrl) => {
  try {
    const target = new URL(targetUrl)
    const server = new URL(configuredServerUrl)
    const isApiPath = target.pathname === '/api' || target.pathname.startsWith('/api/')
    return isApiPath && target.origin === server.origin
  } catch {
    return false
  }
}

/**
 * Merge Electron's cookie-store view into a request after Chromium's SameSite
 * filtering. This keeps the JWT HttpOnly (renderer code never receives it)
 * while allowing the trusted file:// renderer to call its configured backend.
 */
export const attachBackendSessionCookies = (requestHeaders, sessionCookieHeader) => {
  const headers = { ...(requestHeaders || {}) }
  const cookieHeader = mergeCookieHeaders(
    readHeaderCaseInsensitive(headers, 'Cookie'),
    sessionCookieHeader,
  )

  deleteHeaderCaseInsensitive(headers, 'Cookie')
  if (cookieHeader) headers.Cookie = cookieHeader
  return headers
}
