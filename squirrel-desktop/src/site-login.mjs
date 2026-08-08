import { BrowserWindow, session } from 'electron'
import { clearBilibiliPlaybackCache } from './playback/providers/bilibili/index.mjs'
import { resolveYouTubeOAuthRevoke, resolveYouTubeOAuthSetup, resolveYouTubeOAuthStatus } from './playback/providers/youtube/index.mjs'
import { mergeBilibiliFileCookieFallback } from './bilibili-cookie-file.mjs'
import {
  normalizeTargetUrl,
  isBilibiliCookieTarget,
} from './cookie-header.mjs'
import { getConfiguredServerUrl } from './ipc-server-config.mjs'
import { exportSiteCookiesToBackend } from './site-cookie-export.mjs'
import {
  APP_ICON_PATH,
  APP_NAME,
  SITE_SESSION_STORAGE_TYPES,
} from './constants.mjs'

const SITE_LOGIN_PROFILES = {
  youtube: {
    label: 'YouTube',
    loginUrl: 'https://accounts.google.com/ServiceLogin?service=youtube&continue=https%3A%2F%2Fwww.youtube.com%2F',
    cookieHosts: ['youtube.com', 'google.com'],
    allowedHosts: ['youtube.com', 'google.com', 'accounts.google.com', 'gstatic.com', 'googleusercontent.com'],
    storageOrigins: ['https://www.youtube.com', 'https://m.youtube.com', 'https://accounts.google.com', 'https://google.com'],
    signedInCookieNames: ['SID', 'SAPISID', 'APISID', '__Secure-1PSID', '__Secure-3PSID'],
  },
  bilibili: {
    label: 'Bilibili',
    loginUrl: 'https://passport.bilibili.com/login',
    cookieHosts: ['bilibili.com'],
    allowedHosts: ['bilibili.com', 'passport.bilibili.com', 'geetest.com'],
    storageOrigins: ['https://www.bilibili.com', 'https://passport.bilibili.com', 'https://bilibili.com'],
    signedInCookieNames: ['SESSDATA'],
    // Session cookies are exported to the backend after a successful login so
    // backend-side check_login_status/import/sync can use them (the backend may
    // be remote — cookies are pushed via POST /api/site-cookies/{site}).
    exportCookiesToBackend: true,
  },
}

const SITE_LOGIN_ALIASES = {
  'b23.tv': 'bilibili',
  'bilibili.com': 'bilibili',
  'youtu.be': 'youtube',
  'youtube.com': 'youtube',
}

const normalizeSiteName = (siteName) => {
  const rawValue = String(siteName || '').trim().toLowerCase()
  if (!rawValue) {
    return ''
  }

  let normalizedSite = rawValue.replace(/^\./, '')
  try {
    normalizedSite = new URL(rawValue.includes('://') ? rawValue : `https://${rawValue}`).hostname
      .toLowerCase()
      .replace(/^www\./, '')
      .replace(/^\./, '')
  } catch {
    console.debug('[squirrel-desktop] site-login: normalizeSiteName failed', rawValue)
    normalizedSite = normalizedSite.replace(/^www\./, '')
  }

  return SITE_LOGIN_ALIASES[normalizedSite] || normalizedSite
}

export const getSiteLoginProfile = (siteName) => {
  const normalizedSite = normalizeSiteName(siteName)
  return SITE_LOGIN_PROFILES[normalizedSite] ? { siteName: normalizedSite, ...SITE_LOGIN_PROFILES[normalizedSite] } : null
}

export const getCookieProfileForUrl = (targetUrl) => {
  if (isBilibiliCookieTarget(targetUrl)) return getSiteLoginProfile('bilibili')
  return null
}

const hostMatchesLoginProfile = (hostname, hosts) => {
  const normalizedHost = String(hostname || '').replace(/^\./, '').toLowerCase()
  return hosts.some((host) => normalizedHost === host || normalizedHost.endsWith(`.${host}`))
}

const getDesktopSiteCookies = async (profile, hosts = profile.cookieHosts) => {
  const cookies = await session.defaultSession.cookies.get({})
  return cookies.filter((cookie) => hostMatchesLoginProfile(cookie.domain, hosts))
}

const buildSessionCookieHeaderForUrl = async (targetUrl) => {
  const profile = getCookieProfileForUrl(targetUrl)
  try {
    const cookies = profile
      ? await getDesktopSiteCookies(profile)
      : await session.defaultSession.cookies.get({ url: targetUrl })
    return cookies
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join('; ')
  } catch {
    console.debug('[squirrel-desktop] site-login: buildSessionCookieHeaderForUrl failed', targetUrl)
    return ''
  }
}

export const buildCookieHeaderForUrl = async (targetUrl) => {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    return ''
  }

  const sessionHeader = await buildSessionCookieHeaderForUrl(normalizedUrl)
  if (!isBilibiliCookieTarget(normalizedUrl)) {
    return sessionHeader
  }

  // Bilibili requests (playurl/API via ipc-playback, media segments via
  // media-headers attachCookies, subtitles, search) share one merged cookie
  // set: session SESSDATA wins; without it fall back to the backend-synced
  // cookie file so desktop playback resolves HD instead of 480p/360p.
  return mergeBilibiliFileCookieFallback(sessionHeader)
}

const buildYouTubeDesktopLoginStatusFromOAuth = (profile, oauthState) => {
  const status = String(oauthState?.status || 'not_configured')
  const loggedIn = status === 'authenticated' || status === 'already_authenticated'
  const messages = {
    authenticated: 'TV 授权有效',
    already_authenticated: 'TV 授权有效',
    pending: 'TV 授权中',
    expired: 'TV 授权已过期',
    error: `TV 授权异常: ${oauthState?.error || 'Unknown error'}`,
    not_configured: '未配置 TV 授权',
    done: 'TV 授权已清除',
  }

  return {
    site_name: profile.siteName,
    supported: true,
    logged_in: loggedIn,
    message: messages[status] || `TV 授权状态: ${status}`,
    checked_at: new Date().toISOString(),
    source: 'desktop',
    cookie_count: 0,
    oauth_status: status === 'already_authenticated' ? 'authenticated' : status,
    oauth_account: oauthState?.account || null,
    verification_url: oauthState?.verification_url || null,
    user_code: oauthState?.user_code || null,
  }
}

const buildYouTubeDesktopLoginStatus = async (profile) => {
  try {
    return buildYouTubeDesktopLoginStatusFromOAuth(profile, await resolveYouTubeOAuthStatus())
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error || 'Unknown error')
    return {
      site_name: profile.siteName,
      supported: true,
      logged_in: false,
      message: `TV 授权检测失败: ${message}`,
      checked_at: new Date().toISOString(),
      source: 'desktop',
      cookie_count: 0,
      oauth_status: 'error',
      oauth_account: null,
    }
  }
}

export const buildDesktopSiteLoginStatus = async (siteName) => {
  const profile = getSiteLoginProfile(siteName)
  if (!profile) {
    return {
      site_name: normalizeSiteName(siteName),
      supported: false,
      logged_in: false,
      message: '桌面端暂不支持该站点登录',
      checked_at: new Date().toISOString(),
      source: 'desktop',
      cookie_count: 0,
    }
  }

  if (profile.siteName === 'youtube') {
    return buildYouTubeDesktopLoginStatus(profile)
  }

  const cookies = await getDesktopSiteCookies(profile)
  const cookieNames = new Set(cookies.map((cookie) => cookie.name))
  const canConfirmLogin = profile.signedInCookieNames.length > 0
  const hasSignedInCookie = canConfirmLogin
    && profile.signedInCookieNames.some((name) => cookieNames.has(name))

  return {
    site_name: profile.siteName,
    supported: true,
    logged_in: hasSignedInCookie,
    message: hasSignedInCookie
      ? '桌面会话有效'
      : (canConfirmLogin ? '未发现桌面登录会话' : '该站点无法自动确认桌面登录态'),
    checked_at: new Date().toISOString(),
    source: 'desktop',
    cookie_count: cookies.length,
  }
}

const removeDesktopSiteCookies = async (profile) => {
  const hosts = Array.from(new Set([...profile.cookieHosts, ...profile.allowedHosts]))
  const cookies = await getDesktopSiteCookies(profile, hosts)
  for (const cookie of cookies) {
    const domain = String(cookie.domain || '').replace(/^\./, '')
    const protocol = cookie.secure ? 'https' : 'http'
    await session.defaultSession.cookies.remove(`${protocol}://${domain}${cookie.path || '/'}`, cookie.name)
  }
  await session.defaultSession.cookies.flushStore()
}

const clearDesktopSiteStorage = async (profile) => {
  for (const origin of profile.storageOrigins || []) {
    await session.defaultSession.clearStorageData({
      origin,
      storages: SITE_SESSION_STORAGE_TYPES,
    })
  }
  session.defaultSession.flushStorageData()
}

const sessionCookieFetchImpl = (url, options = {}) => session.defaultSession.fetch(url, options)

/**
 * Export a site's session cookies to the configured backend via its upload API.
 * Exposed as `desktop:site-login-export-cookies` for a manual re-export.
 */
export const exportSiteCookiesForSite = async (siteName) => {
  const profile = getSiteLoginProfile(siteName)
  if (!profile) {
    return { ok: false, reason: 'unsupported-site', message: '桌面端暂不支持该站点登录' }
  }
  if (!profile.exportCookiesToBackend) {
    return { ok: false, reason: 'not-exportable', message: '该站点登录态不通过 Cookie 导出' }
  }
  const cookies = await getDesktopSiteCookies(profile)
  return exportSiteCookiesToBackend({
    siteName: profile.siteName,
    cookies,
    serverUrl: getConfiguredServerUrl(),
    fetchImpl: sessionCookieFetchImpl,
  })
}

const attachCookieExportResult = async (profile, status) => {
  if (status?.logged_in !== true || !profile?.exportCookiesToBackend) {
    return status
  }
  try {
    const cookies = await getDesktopSiteCookies(profile)
    const exportResult = await exportSiteCookiesToBackend({
      siteName: profile.siteName,
      cookies,
      serverUrl: getConfiguredServerUrl(),
      fetchImpl: sessionCookieFetchImpl,
    })
    return { ...status, cookie_export: exportResult }
  } catch (error) {
    return {
      ...status,
      cookie_export: { ok: false, reason: 'export-error', message: error?.message || String(error) },
    }
  }
}

export const clearDesktopSiteSession = async (siteName) => {
  const profile = getSiteLoginProfile(siteName)
  if (!profile) {
    return buildDesktopSiteLoginStatus(siteName)
  }

  if (profile.siteName === 'youtube') {
    await resolveYouTubeOAuthRevoke()
    return buildDesktopSiteLoginStatus(profile.siteName)
  }

  await clearDesktopSiteStorage(profile)
  await removeDesktopSiteCookies(profile)
  if (profile.siteName === 'bilibili') {
    clearBilibiliPlaybackCache()
  }
  return buildDesktopSiteLoginStatus(profile.siteName)
}

export const openDesktopSiteLoginWindow = async (siteName, parentWindow) => {
  const profile = getSiteLoginProfile(siteName)
  if (!profile) {
    return buildDesktopSiteLoginStatus(siteName)
  }

  if (profile.siteName === 'youtube') {
    return buildYouTubeDesktopLoginStatusFromOAuth(profile, await resolveYouTubeOAuthSetup())
  }

  const loginWindow = new BrowserWindow({
    width: 1120,
    height: 820,
    minWidth: 900,
    minHeight: 640,
    title: `${APP_NAME} - ${profile.label} Login`,
    icon: APP_ICON_PATH,
    parent: parentWindow && !parentWindow.isDestroyed() ? parentWindow : undefined,
    modal: false,
    webPreferences: {
      session: session.defaultSession,
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
  })

  if (profile.userAgent) {
    loginWindow.webContents.setUserAgent(profile.userAgent)
  }
  if (profile.userAgentMetadata) {
    loginWindow.webContents.debugger.attach('1.3')
    await loginWindow.webContents.debugger.sendCommand('Network.setUserAgentOverride', {
      userAgent: profile.userAgent,
      acceptLanguage: profile.acceptLanguage,
      platform: profile.platform,
      userAgentMetadata: profile.userAgentMetadata,
    })
  }

  loginWindow.webContents.setWindowOpenHandler(({ url }) => {
    const normalizedUrl = normalizeTargetUrl(url)
    if (!normalizedUrl) {
      return { action: 'deny' }
    }

    const hostname = new URL(normalizedUrl).hostname
    if (!hostMatchesLoginProfile(hostname, profile.allowedHosts)) {
      return { action: 'deny' }
    }

    loginWindow.loadURL(normalizedUrl, profile.userAgent ? { userAgent: profile.userAgent } : undefined)
    return { action: 'deny' }
  })

  loginWindow.webContents.on('will-navigate', (event, url) => {
    const normalizedUrl = normalizeTargetUrl(url)
    if (!normalizedUrl) {
      event.preventDefault()
      return
    }

    const hostname = new URL(normalizedUrl).hostname
    if (!hostMatchesLoginProfile(hostname, profile.allowedHosts)) {
      event.preventDefault()
    }
  })

  await loginWindow.loadURL(profile.loginUrl, profile.userAgent ? { userAgent: profile.userAgent } : undefined)
  loginWindow.show()

  return new Promise((resolve, reject) => {
    const canAutoConfirmLogin = profile.signedInCookieNames.length > 0
    let settled = false
    let loginCheckTimer = null

    const clearLoginWatchers = () => {
      if (loginCheckTimer) {
        clearInterval(loginCheckTimer)
        loginCheckTimer = null
      }
      session.defaultSession.cookies.removeListener('changed', handleCookieChanged)
    }

    const resolveWithStatus = (status) => {
      if (settled) return
      settled = true
      clearLoginWatchers()
      if (profile.siteName === 'bilibili') {
        clearBilibiliPlaybackCache()
      }
      // Non-destructive: a failed cookie export must not break the login UX —
      // the result is surfaced on the status as `cookie_export`.
      Promise.resolve(attachCookieExportResult(profile, status)).then(resolve).catch(resolve)
    }

    const checkLoginStatus = () => {
      buildDesktopSiteLoginStatus(profile.siteName)
        .then((status) => {
          if (!status.logged_in) return
          if (!loginWindow.isDestroyed()) {
            loginWindow.close()
          }
          resolveWithStatus(status)
        })
        .catch(reject)
    }

    function handleCookieChanged(_event, cookie) {
      if (hostMatchesLoginProfile(cookie?.domain, profile.cookieHosts)) {
        checkLoginStatus()
      }
    }

    if (canAutoConfirmLogin) {
      session.defaultSession.cookies.on('changed', handleCookieChanged)
      checkLoginStatus()
      loginCheckTimer = setInterval(checkLoginStatus, 1200)
    }

    loginWindow.once('closed', () => {
      if (settled) return
      buildDesktopSiteLoginStatus(profile.siteName)
        .then(resolveWithStatus)
        .catch(reject)
    })
  })
}
