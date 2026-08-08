import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { bilibiliCookieFilePath } from './constants.mjs'
import { mergeCookieHeaders } from './cookie-header.mjs'

/**
 * Bilibili cookie-file fallback for desktop requests.
 *
 * When the Electron session has no bilibili SESSDATA (anonymous), playback
 * resolution would degrade to 480p/360p. This module falls back to the
 * backend-synced cookie file (config/site_cookies/bilibili.txt, populated by
 * the backend's CookieCloud import) so the playurl API and the media-segment
 * requests are served with the browser login.
 *
 * Line parsing mirrors the backend
 * (squirrel-backend/infrastructure/site_catalog/cookies.py ->
 * http.cookiejar.MozillaCookieJar._really_load):
 *   - `#HttpOnly_` prefix marks a real cookie line, not a comment
 *   - other `#` / `$` / blank lines are skipped
 *   - fields are TAB-separated, exactly 7
 *   - secure / domain-specified flags are `TRUE` / `FALSE`
 * Deliberate deviations (documented for the next maintainer):
 *   - a malformed line is skipped instead of rejecting the whole file
 *     (the backend raises and returns nothing); this is strictly more robust
 *     and only differs on corrupted input
 *   - cookies are filtered by the bilibili profile domain (bilibili.com
 *     suffix) rather than the per-URL top-level domain, because media hosts
 *     (bilivideo.com / hdslb.com / acgvideo.com) still need these cookies —
 *     the backend's URL-TLD filter would drop them for media URLs
 *   - expired cookies are kept, matching the backend's
 *     `ignore_discard=True, ignore_expires=True` load
 *
 * Deliberately pure (no Electron imports) so the parsing and merge contract
 * are unit-testable under plain `node --test`.
 */

const HTTPONLY_PREFIX = '#HttpOnly_'
const BILIBILI_DOMAIN_SUFFIX = 'bilibili.com'

export const hasCookieName = (cookieHeader, name) => {
  const target = String(name || '').trim()
  if (!target) {
    return false
  }
  const escaped = target.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return new RegExp(`(?:^|;)\\s*${escaped}=`).test(String(cookieHeader || ''))
}

export const parseNetscapeCookieFile = (content) => {
  const cookies = []
  for (const rawLine of String(content || '').split(/\r?\n/)) {
    let line = rawLine
    if (line.startsWith(HTTPONLY_PREFIX)) {
      line = line.slice(HTTPONLY_PREFIX.length)
    }
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#') || trimmed.startsWith('$')) {
      continue
    }

    const fields = line.split('\t')
    if (fields.length !== 7) {
      continue
    }
    const [domain, domainSpecified, cookiePath, secure, expires, name, value] = fields
    if (!name) {
      continue
    }

    cookies.push({
      domain,
      domainSpecified: domainSpecified === 'TRUE',
      path: cookiePath,
      secure: secure === 'TRUE',
      expires: expires === '' ? null : Number.parseInt(expires, 10),
      name,
      value,
    })
  }
  return cookies
}

const matchesBilibiliDomain = (domain) => {
  const normalized = String(domain || '').replace(/^\./, '').toLowerCase()
  return normalized === BILIBILI_DOMAIN_SUFFIX
    || normalized.endsWith(`.${BILIBILI_DOMAIN_SUFFIX}`)
}

export const resolveBilibiliCookieFilePath = () => {
  const envPath = process.env.BILIBILI_COOKIE_FILE
  return envPath ? path.resolve(envPath) : bilibiliCookieFilePath
}

export const readBilibiliCookieFileHeader = async ({ filePath = resolveBilibiliCookieFilePath() } = {}) => {
  try {
    const content = await readFile(filePath, 'utf8')
    const pairs = parseNetscapeCookieFile(content)
      .filter((cookie) => matchesBilibiliDomain(cookie.domain))
      .map((cookie) => `${cookie.name}=${cookie.value}`)
    return pairs.join('; ')
  } catch (err) {
    console.debug('[squirrel-desktop] bilibili cookie file fallback unavailable', err?.message || String(err))
    return ''
  }
}

/**
 * Merge contract (shared by playurl/API and media-segment requests):
 *   1. session header has a bilibili SESSDATA -> session wins untouched
 *      (no file read at all)
 *   2. otherwise read the cookie file; on name collisions the session value
 *      wins (live desktop state is newer than the synced file), the file fills
 *      the gaps (SESSDATA / buvid3 / b_nut / b_lsid / DedeUserID / bili_jct...)
 *   3. file missing/unreadable -> anonymous, session header as-is
 */
export const mergeBilibiliFileCookieFallback = async (sessionCookieHeader, { filePath } = {}) => {
  const sessionHeader = String(sessionCookieHeader || '').trim()
  if (hasCookieName(sessionHeader, 'SESSDATA')) {
    return sessionHeader
  }

  const fileHeader = await readBilibiliCookieFileHeader({ filePath })
  if (!fileHeader) {
    return sessionHeader
  }

  return mergeCookieHeaders(fileHeader, sessionHeader)
}
