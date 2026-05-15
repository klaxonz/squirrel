import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { app, BrowserWindow, clipboard, ipcMain, Menu, session, shell } from 'electron'
import { clearBilibiliPlaybackCache, resolveBilibiliPlayback } from './playback/providers/bilibili/index.mjs'
import { resolvePornhubPlayback } from './playback/providers/pornhub/index.mjs'
import { resolveYouPornPlayback } from './playback/providers/youporn/index.mjs'
import {
  prewarmYouTubePlayback,
  resolveYouTubeOAuthRevoke,
  resolveYouTubeOAuthSetup,
  resolveYouTubeOAuthStatus,
  resolveYouTubePlayback,
  resolveYouTubeSubtitles,
} from './playback/providers/youtube/index.mjs'
import { searchRemoteVideos } from './search/providers/index.mjs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const repoRoot = path.resolve(__dirname, '..', '..')
const javdbCookieFilePath = path.join(repoRoot, 'config', 'site_cookies', 'javdb.txt')
const pornhubCookieFilePath = path.join(repoRoot, 'config', 'site_cookies', 'pornhub.txt')
const youpornCookieFilePath = path.join(repoRoot, 'config', 'site_cookies', 'youporn.txt')
const youtubeOAuthStateFilePath = path.join(repoRoot, 'config', 'youtube_oauth.json')
const desktopChromeVersion = process.versions.chrome || '124.0.0.0'
const desktopChromeMajorVersion = desktopChromeVersion.split('.')[0] || '124'
const desktopChromeUserAgent = `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${desktopChromeVersion} Safari/537.36`
const desktopChromeAcceptLanguage = 'en-US,en;q=0.9'
const desktopChromeClientHints = {
  'sec-ch-ua': `"Chromium";v="${desktopChromeMajorVersion}", "Google Chrome";v="${desktopChromeMajorVersion}", "Not-A.Brand";v="99"`,
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"',
}
const javdbOrigin = 'https://javdb.com'
const javdbReferer = `${javdbOrigin}/`
const javdbLoginCheckUrl = `${javdbOrigin}/users/collection_actors`
const javdbLoginRedirectPattern = /\/users\/(?:sign_in|login)|\/(?:sign_in|login)/i
const javdbLoginPagePattern = /<title>\s*sign in\s*\|\s*javdb|action="\/users\/sign_in"|name="user\[(?:login|email)\]"/i
const javdbErrorPagePattern = /<title>\s*just a moment|cf-error-details|error code 502|bad gateway/i
const pornhubOrigin = 'https://www.pornhub.com'
const pornhubReferer = `${pornhubOrigin}/`
const pornhubAgeGateCookieHeader = 'age_verified=1; accessAgeDisclaimerPH=1; accessAgeDisclaimerUK=1; accessPH=1'
const youpornAgeGateCookieHeader = 'showAgeDisclaimer=1; access=1; accessPH=1'
const pornhubLoggedInPattern = /"loggedIn(?:Context)?":\s*true/i
const pornhubLoggedOutPattern = /"loggedIn(?:Context)?":\s*false/i
const pornhubUsernamePattern = /"username"\s*:\s*"([^"]+)"/i
const pornhubDataUsernamePattern = /data-username="([^"]+)"/i
const pornhubProfileLinkPattern = /<a[^>]+class="username"[^>]+href="\/users\/([^"/?#]+)"/i
const pornhubProfileBlockPattern = /<div[^>]+class="profile"[\s\S]*?class="js_userName"[^>]*>([^<]+)</i
const pornhubProfileStatusPattern = /class="userUserStatus[^"]*">\s*See Your Profile/i
const SITE_SESSION_STORAGE_TYPES = [
  'cookies',
  'filesystem',
  'indexdb',
  'localstorage',
  'serviceworkers',
  'cachestorage',
  'websql',
]

const APP_NAME = 'Squirrel'
const DEFAULT_APP_URL = 'http://127.0.0.1:8001'
const WINDOW_STATE_FILE_NAME = 'window-state.json'
const WINDOW_STATE_SAVE_DELAY_MS = 250
const DEFAULT_WINDOW_STATE = {
  width: 1440,
  height: 960,
  minWidth: 1100,
  minHeight: 720,
}

const SERVER_CONFIG_FILE = 'server-config.json'

if (!process.env.YOUTUBE_OAUTH_STATE_FILE && fs.existsSync(youtubeOAuthStateFilePath)) {
  process.env.YOUTUBE_OAUTH_STATE_FILE = youtubeOAuthStateFilePath
}

const resolveRendererUrl = () => {
  const value = String(
    process.env.DESKTOP_RENDERER_URL
    || process.env.DESKTOP_APP_URL
    || DEFAULT_APP_URL
  ).trim()

  try {
    return new URL(value || DEFAULT_APP_URL).toString()
  } catch {
    return DEFAULT_APP_URL
  }
}

const rendererUrl = resolveRendererUrl()
const rendererOrigin = new URL(rendererUrl).origin

// ── Server config persistence ──────────────────────────────────────────────

const getServerConfigPath = () => {
  return path.join(app.getPath('userData'), SERVER_CONFIG_FILE)
}

const loadServerConfig = () => {
  try {
    const raw = fs.readFileSync(getServerConfigPath(), 'utf8')
    const parsed = JSON.parse(raw)
    const url = typeof parsed?.serverUrl === 'string' ? parsed.serverUrl.trim() : ''
    if (url) {
      try {
        return new URL(url).origin
      } catch {
        return ''
      }
    }
    return ''
  } catch {
    return ''
  }
}

const saveServerConfig = (url) => {
  try {
    fs.mkdirSync(path.dirname(getServerConfigPath()), { recursive: true })
    fs.writeFileSync(getServerConfigPath(), JSON.stringify({ serverUrl: url }, null, 2), 'utf8')
    return true
  } catch {
    return false
  }
}

const normalizeTargetUrl = (targetUrl) => {
  const value = String(targetUrl || '').trim()
  if (!value) {
    return ''
  }

  try {
    return new URL(value).toString()
  } catch {
    return ''
  }
}

const isJavdbCookieTarget = (targetUrl) => {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    return false
  }

  try {
    const hostname = new URL(normalizedUrl).hostname.toLowerCase()
    return hostname === 'javdb.com' || hostname.endsWith('.javdb.com')
  } catch {
    return false
  }
}

const isBilibiliCookieTarget = (targetUrl) => {
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
    return false
  }
}

const isPornhubCookieTarget = (targetUrl) => {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    return false
  }

  try {
    const hostname = new URL(normalizedUrl).hostname.toLowerCase()
    return hostname === 'pornhub.com'
      || hostname.endsWith('.pornhub.com')
      || hostname.endsWith('.phncdn.com')
  } catch {
    return false
  }
}

const isYouPornCookieTarget = (targetUrl) => {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    return false
  }

  try {
    const hostname = new URL(normalizedUrl).hostname.toLowerCase()
    return hostname === 'youporn.com'
      || hostname.endsWith('.youporn.com')
      || hostname.endsWith('.ypncdn.com')
  } catch {
    return false
  }
}

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
  },
  javdb: {
    label: 'JavDB',
    loginUrl: 'https://javdb.com/users/sign_in',
    userAgent: desktopChromeUserAgent,
    acceptLanguage: desktopChromeAcceptLanguage,
    platform: 'Windows',
    cookieHosts: ['javdb.com'],
    allowedHosts: ['javdb.com'],
    storageOrigins: ['https://javdb.com'],
    signedInCookieNames: [],
  },
  pornhub: {
    label: 'Pornhub',
    loginUrl: 'https://www.pornhub.com/login',
    cookieHosts: ['pornhub.com'],
    allowedHosts: ['pornhub.com'],
    storageOrigins: ['https://www.pornhub.com', 'https://pornhub.com'],
    signedInCookieNames: [],
  },
  youporn: {
    label: 'YouPorn',
    loginUrl: 'https://www.youporn.com/login',
    cookieHosts: ['youporn.com'],
    allowedHosts: ['youporn.com'],
    storageOrigins: ['https://www.youporn.com', 'https://youporn.com'],
    signedInCookieNames: [],
  },
}

const SITE_LOGIN_ALIASES = {
  'b23.tv': 'bilibili',
  'bilibili.com': 'bilibili',
  'javdb.com': 'javdb',
  'pornhub.com': 'pornhub',
  'youtu.be': 'youtube',
  'youtube.com': 'youtube',
  'youporn.com': 'youporn',
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
    normalizedSite = normalizedSite.replace(/^www\./, '')
  }

  return SITE_LOGIN_ALIASES[normalizedSite] || normalizedSite
}

const getSiteLoginProfile = (siteName) => {
  const normalizedSite = normalizeSiteName(siteName)
  return SITE_LOGIN_PROFILES[normalizedSite] ? { siteName: normalizedSite, ...SITE_LOGIN_PROFILES[normalizedSite] } : null
}

const hostMatchesLoginProfile = (hostname, hosts) => {
  const normalizedHost = String(hostname || '').replace(/^\./, '').toLowerCase()
  return hosts.some((host) => normalizedHost === host || normalizedHost.endsWith(`.${host}`))
}

const getDesktopSiteCookies = async (profile, hosts = profile.cookieHosts) => {
  const cookies = await session.defaultSession.cookies.get({})
  return cookies.filter((cookie) => hostMatchesLoginProfile(cookie.domain, hosts))
}

const buildCookieHeaderFromCookies = (cookies) => {
  return cookies.map((cookie) => `${cookie.name}=${cookie.value}`).join('; ')
}

const writeJavdbCookieFile = (cookies) => {
  const javdbCookies = cookies.filter((cookie) => hostMatchesLoginProfile(cookie.domain, ['javdb.com']))
  if (!javdbCookies.length) {
    return
  }

  fs.mkdirSync(path.dirname(javdbCookieFilePath), { recursive: true })
  const lines = ['# Netscape HTTP Cookie File']
  for (const cookie of javdbCookies) {
    const domain = String(cookie.domain || '').trim() || 'javdb.com'
    const includeSubdomains = domain.startsWith('.') ? 'TRUE' : 'FALSE'
    const cookiePath = String(cookie.path || '/').trim() || '/'
    const secure = cookie.secure ? 'TRUE' : 'FALSE'
    const expires = Number.isFinite(cookie.expirationDate) ? Math.floor(cookie.expirationDate) : 0
    const prefix = cookie.httpOnly ? '#HttpOnly_' : ''
    lines.push([
      `${prefix}${domain}`,
      includeSubdomains,
      cookiePath,
      secure,
      String(expires),
      cookie.name,
      cookie.value,
    ].join('\t'))
  }
  fs.writeFileSync(javdbCookieFilePath, `${lines.join('\n')}\n`, 'utf8')
}

const checkJavdbDesktopPageLogin = async (cookieHeader) => {
  const response = await session.defaultSession.fetch(javdbLoginCheckUrl, {
    headers: {
      'Accept-Language': desktopChromeAcceptLanguage,
      Origin: javdbOrigin,
      Referer: javdbReferer,
      'User-Agent': desktopChromeUserAgent,
      Cookie: cookieHeader,
    },
    redirect: 'manual',
  })
  const body = await response.text()
  const location = response.headers.get('Location') || response.headers.get('location') || ''
  const finalUrl = response.url || javdbLoginCheckUrl

  if (response.status === 401) {
    return { logged_in: false, message: `认证失败 (status=${response.status})` }
  }
  if ([403, 404, 429, 500, 502, 503, 504].includes(response.status)) {
    return { logged_in: false, message: `检测失败: 被拒绝访问 (status=${response.status})` }
  }
  if ([301, 302, 303, 307, 308].includes(response.status) && javdbLoginRedirectPattern.test(location)) {
    return { logged_in: false, message: '被重定向到登录页' }
  }
  if (javdbLoginRedirectPattern.test(finalUrl) || javdbLoginPagePattern.test(body)) {
    return { logged_in: false, message: '返回内容显示为登录页' }
  }
  if (javdbErrorPagePattern.test(body)) {
    return { logged_in: false, message: '检测失败: 返回内容显示为站点错误页' }
  }

  return { logged_in: true, message: '桌面会话有效' }
}

const buildJavdbDesktopLoginStatus = async (profile, cookies) => {
  const sessionCookieHeader = buildCookieHeaderFromCookies(cookies)
  const fileCookieHeader = readJavdbCookieFileHeader()
  const cookieHeader = mergeCookieHeaders(fileCookieHeader, sessionCookieHeader)
  if (!cookieHeader) {
    return {
      site_name: profile.siteName,
      supported: true,
      logged_in: false,
      message: '未发现桌面登录会话',
      checked_at: new Date().toISOString(),
      source: 'desktop',
      cookie_count: cookies.length,
    }
  }

  try {
    const status = await checkJavdbDesktopPageLogin(cookieHeader)
    if (status.logged_in && sessionCookieHeader) {
      writeJavdbCookieFile(cookies)
    }
    return {
      site_name: profile.siteName,
      supported: true,
      ...status,
      checked_at: new Date().toISOString(),
      source: 'desktop',
      cookie_count: cookies.length,
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error || 'Unknown error')
    return {
      site_name: profile.siteName,
      supported: true,
      logged_in: false,
      message: `检测失败: ${message}`,
      checked_at: new Date().toISOString(),
      source: 'desktop',
      cookie_count: cookies.length,
    }
  }
}

const extractPornhubDesktopUsername = (body) => {
  const match = pornhubProfileLinkPattern.exec(body)
    || pornhubUsernamePattern.exec(body)
    || pornhubDataUsernamePattern.exec(body)
  const username = String(match?.[1] || '').trim()
  return username || null
}

const checkPornhubDesktopPageLogin = async (cookieHeader) => {
  const response = await session.defaultSession.fetch(pornhubReferer, {
    headers: {
      'Accept-Language': 'en-US,en;q=0.9',
      Origin: pornhubOrigin,
      Referer: pornhubReferer,
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
      Cookie: cookieHeader,
    },
    redirect: 'follow',
  })
  const body = await response.text()
  const finalUrl = response.url || pornhubReferer

  if (response.status === 401) {
    return { logged_in: false, message: `被拒绝访问 (status=${response.status})` }
  }
  if ([403, 429, 500, 502, 503, 504].includes(response.status)) {
    return { logged_in: false, message: `检测失败: 被拒绝访问 (status=${response.status})` }
  }
  if (finalUrl.includes('/login') || finalUrl.includes('/users/login')) {
    return { logged_in: false, message: '被重定向到登录页' }
  }

  const profileMatch = pornhubProfileBlockPattern.exec(body)
  const username = String(profileMatch?.[1] || '').trim() || extractPornhubDesktopUsername(body)
  if (profileMatch || pornhubProfileStatusPattern.test(body)) {
    return { logged_in: true, username, message: '桌面会话有效' }
  }
  if (pornhubLoggedInPattern.test(body) || (pornhubProfileLinkPattern.test(body) && username)) {
    return { logged_in: true, username, message: '桌面会话有效' }
  }

  return {
    logged_in: false,
    message: pornhubLoggedOutPattern.test(body) ? '未登录' : '未检测到登录标记',
  }
}

const buildPornhubDesktopLoginStatus = async (profile, cookies) => {
  const cookieHeader = cookies.map((cookie) => `${cookie.name}=${cookie.value}`).join('; ')
  if (!cookieHeader) {
    return {
      site_name: profile.siteName,
      supported: true,
      logged_in: false,
      message: '未发现桌面登录会话',
      checked_at: new Date().toISOString(),
      source: 'desktop',
      cookie_count: cookies.length,
    }
  }

  try {
    const status = await checkPornhubDesktopPageLogin(mergeCookieHeaders(pornhubAgeGateCookieHeader, cookieHeader))
    return {
      site_name: profile.siteName,
      supported: true,
      ...status,
      checked_at: new Date().toISOString(),
      source: 'desktop',
      cookie_count: cookies.length,
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error || 'Unknown error')
    return {
      site_name: profile.siteName,
      supported: true,
      logged_in: false,
      message: `检测失败: ${message}`,
      checked_at: new Date().toISOString(),
      source: 'desktop',
      cookie_count: cookies.length,
    }
  }
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

const buildDesktopSiteLoginStatus = async (siteName) => {
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
  if (profile.siteName === 'javdb') {
    return buildJavdbDesktopLoginStatus(profile, cookies)
  }
  if (profile.siteName === 'pornhub') {
    return buildPornhubDesktopLoginStatus(profile, cookies)
  }

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

const clearDesktopSiteSession = async (siteName) => {
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
  if (profile.siteName === 'javdb' && fs.existsSync(javdbCookieFilePath)) {
    fs.rmSync(javdbCookieFilePath)
  }
  return buildDesktopSiteLoginStatus(profile.siteName)
}

const openDesktopSiteLoginWindow = async (siteName, parentWindow) => {
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
      || profile.siteName === 'javdb'
      || profile.siteName === 'pornhub'
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
      resolve(status)
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

const readNetscapeCookieFileHeader = (cookieFilePath, domainSuffixes) => {
  if (!fs.existsSync(cookieFilePath)) {
    return ''
  }

  try {
    const raw = fs.readFileSync(cookieFilePath, 'utf8')
    const pairs = []

    for (const rawLine of raw.split(/\r?\n/)) {
      const line = rawLine.trim()
      if (!line) {
        continue
      }

      const normalizedLine = line.startsWith('#HttpOnly_')
        ? line.slice('#HttpOnly_'.length)
        : line

      if (normalizedLine.startsWith('#')) {
        continue
      }

      const parts = normalizedLine.split('\t')
      if (parts.length < 7) {
        continue
      }

      const domain = String(parts[0] || '').replace(/^\./, '').toLowerCase()
      const name = String(parts[5] || '').trim()
      const value = String(parts[6] || '').trim()

      if (!name || !domainSuffixes.some((suffix) => domain.endsWith(suffix))) {
        continue
      }

      pairs.push(`${name}=${value}`)
    }

    return pairs.join('; ')
  } catch {
    return ''
  }
}

const prewarmDesktopPlaybackProviders = () => {
  setTimeout(() => {
    void prewarmYouTubePlayback().catch((error) => {
      console.debug('[squirrel-desktop] YouTube playback prewarm skipped', error?.message || error)
    })
  }, 1000)
}

const readJavdbCookieFileHeader = () => {
  return readNetscapeCookieFileHeader(javdbCookieFilePath, ['javdb.com'])
}

const readPornhubCookieFileHeader = () => {
  return readNetscapeCookieFileHeader(pornhubCookieFilePath, [
    'pornhub.com',
    'phncdn.com',
  ])
}

const readYouPornCookieFileHeader = () => {
  return readNetscapeCookieFileHeader(youpornCookieFilePath, [
    'youporn.com',
    'ypncdn.com',
  ])
}

const mergeCookieHeaders = (...cookieHeaders) => {
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

const isJavdbCloudflareChallengeHtml = (html) => {
  const source = String(html || '')
  if (/<title>\s*JavDB\b/i.test(source)) {
    return false
  }
  return /<title>[^<]*(?:Attention Required|Just a moment)[^<]*<\/title>|please complete the captcha|cf-error-details|cf-turnstile|challenges\.cloudflare\.com\/turnstile/i
    .test(source)
}

const isJavdbAgeGateHtml = (html) => {
  return /over18-modal|href=["'][^"']*\/over18\?respond=1/i.test(String(html || ''))
}

const getCookieProfileForUrl = (targetUrl) => {
  if (isJavdbCookieTarget(targetUrl)) return getSiteLoginProfile('javdb')
  if (isBilibiliCookieTarget(targetUrl)) return getSiteLoginProfile('bilibili')
  if (isPornhubCookieTarget(targetUrl)) return getSiteLoginProfile('pornhub')
  if (isYouPornCookieTarget(targetUrl)) return getSiteLoginProfile('youporn')
  return null
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
    return ''
  }
}

const buildCookieHeaderForUrl = async (targetUrl) => {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    return ''
  }

  const sessionCookieHeader = await buildSessionCookieHeaderForUrl(normalizedUrl)

  if (isJavdbCookieTarget(normalizedUrl)) {
    return mergeCookieHeaders(readJavdbCookieFileHeader(), sessionCookieHeader)
  }

  if (isBilibiliCookieTarget(normalizedUrl)) {
    return sessionCookieHeader
  }

  if (isPornhubCookieTarget(normalizedUrl)) {
    return mergeCookieHeaders(pornhubAgeGateCookieHeader, readPornhubCookieFileHeader(), sessionCookieHeader)
  }

  if (isYouPornCookieTarget(normalizedUrl)) {
    return mergeCookieHeaders(youpornAgeGateCookieHeader, readYouPornCookieFileHeader(), sessionCookieHeader)
  }

  return sessionCookieHeader
}

const createSessionFetch = () => {
  return async (targetUrl, options = {}) => {
    const abortController = new AbortController()
    const timeoutMs = Number(options?.timeoutMs) || 25000
    const timer = setTimeout(() => abortController.abort(), timeoutMs)

    try {
      return await session.defaultSession.fetch(targetUrl, {
        method: options?.method || 'GET',
        headers: options?.headers || {},
        redirect: options?.redirect || 'follow',
        signal: abortController.signal,
      })
    } finally {
      clearTimeout(timer)
    }
  }
}

const JAVDB_AUTO_BYPASS_WAIT_MS = 5000
const CHALLENGE_CHECK_INTERVAL_MS = 500
const DOCUMENT_READ_TIMEOUT_MS = 10000
const TURNSTILE_CLICK_INTERVAL_MS = 2000

const waitForDocumentNavigation = async (browserWindow, targetUrl, userAgent, timeoutMs) => {
  let settled = false
  let timer

  await new Promise((resolve, reject) => {
    const cleanup = () => {
      browserWindow.webContents.off('dom-ready', handleReady)
      browserWindow.webContents.off('did-finish-load', handleReady)
      browserWindow.webContents.off('did-fail-load', handleFail)
      clearTimeout(timer)
    }
    const finish = (callback, value) => {
      if (settled) return
      settled = true
      cleanup()
      callback(value)
    }
    const handleReady = () => finish(resolve)
    const handleFail = (_event, errorCode, errorDescription) => {
      finish(reject, new Error(`Document load failed: ${errorCode} ${errorDescription}`))
    }

    browserWindow.webContents.once('dom-ready', handleReady)
    browserWindow.webContents.once('did-finish-load', handleReady)
    browserWindow.webContents.once('did-fail-load', handleFail)
    timer = setTimeout(() => finish(reject, new Error('Document load timed out')), timeoutMs)

    browserWindow.loadURL(targetUrl, { userAgent }).catch((error) => {
      finish(reject, error)
    })
  })
}

const readBrowserWindowHtml = async (browserWindow) => {
  let timer
  try {
    const html = await Promise.race([
      browserWindow.webContents.executeJavaScript('document.documentElement.outerHTML', true),
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error('Document read timed out')), DOCUMENT_READ_TIMEOUT_MS)
      }),
    ])
    return String(html || '')
  } finally {
    clearTimeout(timer)
  }
}

const waitForDocumentAutoBypass = async (browserWindow, timeoutMs = JAVDB_AUTO_BYPASS_WAIT_MS) => {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (browserWindow.isDestroyed()) {
      throw new Error('JavDB document window was closed')
    }

    try {
      const html = await readBrowserWindowHtml(browserWindow)
      const currentUrl = browserWindow.webContents.getURL()
      if (!isJavdbCloudflareChallengeHtml(html) && !javdbLoginRedirectPattern.test(currentUrl)) {
        return html
      }
    } catch {
      // Page is still navigating.
    }

    await new Promise((resolve) => setTimeout(resolve, CHALLENGE_CHECK_INTERVAL_MS))
  }

  return ''
}

const findJavdbTurnstileClickPoint = async (browserWindow) => {
  try {
    return await browserWindow.webContents.executeJavaScript(`
(() => {
  const isVisible = (rect) => rect && rect.width >= 20 && rect.height >= 20;
  const fromRect = (rect) => ({ x: rect.left + rect.width * 0.3, y: rect.top + rect.height * 0.5 });
  const selectors = [
    'iframe[src*="challenges.cloudflare.com"]',
    'iframe[title*="challenge" i]',
    'iframe[title*="turnstile" i]',
    'input[name="cf-turnstile-response"]',
    '.cf-turnstile',
    '[data-sitekey]',
  ];

  for (const selector of selectors) {
    for (const node of document.querySelectorAll(selector)) {
      let current = node;
      while (current) {
        const rect = current.getBoundingClientRect();
        if (isVisible(rect)) return fromRect(rect);
        current = current.parentElement;
      }
    }
  }
  return null;
})()
`, true)
  } catch {
    return null
  }
}

const attemptJavdbTurnstileClick = async (browserWindow) => {
  const point = await findJavdbTurnstileClickPoint(browserWindow)
  if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y)) {
    return false
  }

  const x = Math.round(point.x)
  const y = Math.round(point.y)
  browserWindow.webContents.focus()
  browserWindow.webContents.sendInputEvent({ type: 'mouseMove', x: x - 12, y })
  browserWindow.webContents.sendInputEvent({ type: 'mouseMove', x, y })
  browserWindow.webContents.sendInputEvent({ type: 'mouseDown', x, y, button: 'left', clickCount: 1 })
  browserWindow.webContents.sendInputEvent({ type: 'mouseUp', x, y, button: 'left', clickCount: 1 })
  return true
}

const waitForJavdbChallengeAutoResolution = async (browserWindow, timeoutMs) => {
  if (browserWindow.isDestroyed()) {
    throw new Error('JavDB document window was closed')
  }

  const deadline = Date.now() + timeoutMs
  let lastHtml = ''
  let lastClickAt = 0
  while (Date.now() < deadline) {
    if (browserWindow.isDestroyed()) {
      throw new Error('JavDB document window was closed')
    }

    try {
      lastHtml = await readBrowserWindowHtml(browserWindow)
      const currentUrl = browserWindow.webContents.getURL()
      if (!isJavdbCloudflareChallengeHtml(lastHtml) && !javdbLoginRedirectPattern.test(currentUrl)) {
        return lastHtml
      }
      if (Date.now() - lastClickAt >= TURNSTILE_CLICK_INTERVAL_MS) {
        const clicked = await attemptJavdbTurnstileClick(browserWindow)
        if (clicked) {
          lastClickAt = Date.now()
        }
      }
    } catch {
      // Page is still navigating.
    }

    await new Promise((resolve) => setTimeout(resolve, CHALLENGE_CHECK_INTERVAL_MS))
  }

  throw new Error('JavDB Cloudflare auto verification timed out')
}

const resolveJavdbAgeGate = async (browserWindow, userAgent, timeoutMs) => {
  const href = String(await browserWindow.webContents.executeJavaScript(`
(() => {
  const link = document.querySelector('.over18-modal a[href*="/over18?respond=1"], a[href*="/over18?respond=1"]');
  return link ? link.getAttribute('href') : '';
})()
`, true) || '').trim()
  if (!href) {
    throw new Error('JavDB age gate confirmation link was not found')
  }

  await waitForDocumentNavigation(browserWindow, new URL(href, javdbOrigin).toString(), userAgent, timeoutMs)
  return readBrowserWindowHtml(browserWindow)
}

const createDocumentBrowserWindow = async (profile) => {
  const documentWindow = new BrowserWindow({
    width: 1280,
    height: 900,
    show: false,
    paintWhenInitiallyHidden: true,
    webPreferences: {
      session: session.defaultSession,
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      backgroundThrottling: false,
    },
  })

  const userAgent = profile?.userAgent || desktopChromeUserAgent
  documentWindow.webContents.setUserAgent(userAgent)

  return { documentWindow, userAgent }
}

const loadDocumentHtmlWithBrowserWindow = async (targetUrl, options = {}) => {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    throw new Error('Invalid document URL')
  }

  const profile = getCookieProfileForUrl(normalizedUrl)
  const timeoutMs = Number(options?.timeoutMs) || 30000
  const challengeTimeoutMs = Number(options?.challengeTimeoutMs) || 120000

  const entry = await createDocumentBrowserWindow(profile)
  const { documentWindow, userAgent } = entry

  try {
    try {
      await waitForDocumentNavigation(documentWindow, normalizedUrl, userAgent, timeoutMs)
    } catch (error) {
      if (!isJavdbCookieTarget(normalizedUrl) || !String(error?.message || '').includes('timed out')) {
        throw error
      }
    }

    let html = await readBrowserWindowHtml(documentWindow)
    if (isJavdbCookieTarget(normalizedUrl) && isJavdbAgeGateHtml(html)) {
      html = await resolveJavdbAgeGate(documentWindow, userAgent, timeoutMs)
    }
    if (isJavdbCookieTarget(normalizedUrl) && isJavdbCloudflareChallengeHtml(html)) {
      const autoBypassedHtml = await waitForDocumentAutoBypass(documentWindow)
      if (autoBypassedHtml) {
        html = autoBypassedHtml
      } else {
        html = await waitForJavdbChallengeAutoResolution(documentWindow, challengeTimeoutMs)
      }
    }
    const finalUrl = documentWindow.webContents.getURL()
    if (isJavdbCookieTarget(normalizedUrl) && javdbLoginRedirectPattern.test(finalUrl)) {
      throw new Error('JavDB desktop session is not logged in')
    }
    return String(html || '')
  } finally {
    if (!documentWindow.isDestroyed() && documentWindow.webContents.isLoading()) {
      documentWindow.webContents.stop()
    }
    if (!documentWindow.isDestroyed()) {
      documentWindow.close()
    }
  }
}

// ── Escape helpers ──────────────────────────────────────────────────────────

const escapeHtml = (value) => {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

const formatWindowTitle = (value) => {
  const title = String(value || '').trim()
  if (!title || title === APP_NAME) {
    return APP_NAME
  }

  return title.endsWith(` - ${APP_NAME}`) ? title : `${title} - ${APP_NAME}`
}

const getWindowStateFilePath = () => {
  return path.join(app.getPath('userData'), WINDOW_STATE_FILE_NAME)
}

const sanitizeDimension = (value, fallback, minimum) => {
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) {
    return fallback
  }

  return Math.max(Math.round(numericValue), minimum)
}

const sanitizeCoordinate = (value) => {
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? Math.round(numericValue) : undefined
}

const loadWindowState = () => {
  try {
    const rawState = fs.readFileSync(getWindowStateFilePath(), 'utf8')
    const parsedState = JSON.parse(rawState)

    return {
      x: sanitizeCoordinate(parsedState.x),
      y: sanitizeCoordinate(parsedState.y),
      width: sanitizeDimension(parsedState.width, DEFAULT_WINDOW_STATE.width, DEFAULT_WINDOW_STATE.minWidth),
      height: sanitizeDimension(parsedState.height, DEFAULT_WINDOW_STATE.height, DEFAULT_WINDOW_STATE.minHeight),
      isMaximized: parsedState.isMaximized === true,
    }
  } catch {
    return {
      width: DEFAULT_WINDOW_STATE.width,
      height: DEFAULT_WINDOW_STATE.height,
      isMaximized: false,
    }
  }
}

const persistWindowState = (mainWindow) => {
  if (!mainWindow || mainWindow.isDestroyed() || mainWindow.isMinimized()) {
    return
  }

  const bounds = mainWindow.isMaximized()
    ? mainWindow.getNormalBounds()
    : mainWindow.getBounds()

  const state = {
    x: bounds.x,
    y: bounds.y,
    width: Math.max(bounds.width, DEFAULT_WINDOW_STATE.minWidth),
    height: Math.max(bounds.height, DEFAULT_WINDOW_STATE.minHeight),
    isMaximized: mainWindow.isMaximized(),
  }

  fs.mkdirSync(path.dirname(getWindowStateFilePath()), { recursive: true })
  fs.writeFileSync(getWindowStateFilePath(), JSON.stringify(state, null, 2), 'utf8')
}

const bindWindowStatePersistence = (mainWindow) => {
  let saveTimer = null

  const scheduleSave = () => {
    if (saveTimer) {
      clearTimeout(saveTimer)
    }

    saveTimer = setTimeout(() => {
      persistWindowState(mainWindow)
      saveTimer = null
    }, WINDOW_STATE_SAVE_DELAY_MS)
  }

  mainWindow.on('resize', scheduleSave)
  mainWindow.on('move', scheduleSave)
  mainWindow.on('maximize', scheduleSave)
  mainWindow.on('unmaximize', scheduleSave)
  mainWindow.on('close', () => {
    if (saveTimer) {
      clearTimeout(saveTimer)
      saveTimer = null
    }
    persistWindowState(mainWindow)
  })
}

const buildShellPageUrl = ({ title, eyebrow, heading, body, status, tone = 'loading' }) => {
  const accent = tone === 'error' ? '#f97373' : '#7dd3fc'
  const actionScript = `window.desktopApp?.reloadApp?.() || window.location.replace(${JSON.stringify(rendererUrl)})`
  const openExternalScript = `window.desktopApp?.openExternal?.(${JSON.stringify(rendererUrl)}) || window.open(${JSON.stringify(rendererUrl)}, '_blank', 'noopener,noreferrer')`

  const html = `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${escapeHtml(formatWindowTitle(title))}</title>
    <style>
      :root {
        color-scheme: dark;
        --bg: #05080c;
        --panel: rgba(12, 18, 26, 0.88);
        --panel-border: rgba(125, 211, 252, 0.16);
        --text: rgba(255, 255, 255, 0.94);
        --muted: rgba(255, 255, 255, 0.62);
        --accent: ${accent};
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        overflow: hidden;
        background:
          radial-gradient(circle at top, rgba(125, 211, 252, 0.12), transparent 36%),
          radial-gradient(circle at bottom right, rgba(56, 189, 248, 0.08), transparent 24%),
          linear-gradient(180deg, #08111a 0%, var(--bg) 100%);
        color: var(--text);
        font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      }
      .shell {
        width: min(36rem, calc(100vw - 2rem));
        padding: 1.5rem;
        border-radius: 1.25rem;
        border: 1px solid var(--panel-border);
        background: var(--panel);
        backdrop-filter: blur(18px);
        box-shadow: 0 24px 80px rgba(0, 0, 0, 0.38);
      }
      .eyebrow {
        margin: 0 0 0.75rem;
        color: var(--accent);
        font-size: 0.78rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
      }
      h1 {
        margin: 0;
        font-size: clamp(1.5rem, 4vw, 2.15rem);
        line-height: 1.1;
      }
      p {
        margin: 0;
        font-size: 0.98rem;
        line-height: 1.7;
        color: var(--muted);
      }
      .copy {
        display: grid;
        gap: 0.9rem;
      }
      .status {
        margin-top: 1.2rem;
        padding: 0.8rem 0.95rem;
        border-radius: 0.85rem;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.06);
        color: var(--muted);
        font-family: "JetBrains Mono", Consolas, monospace;
        font-size: 0.82rem;
        word-break: break-all;
      }
      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        margin-top: 1.2rem;
      }
      button, a {
        appearance: none;
        border: 0;
        cursor: pointer;
        border-radius: 999px;
        padding: 0.8rem 1.15rem;
        font: inherit;
        text-decoration: none;
      }
      .primary {
        background: linear-gradient(135deg, var(--accent), #38bdf8);
        color: #04121e;
        font-weight: 700;
      }
      .secondary {
        background: rgba(255, 255, 255, 0.06);
        color: var(--text);
      }
    </style>
  </head>
  <body>
    <main class="shell">
      <div class="copy">
        <div class="eyebrow">${escapeHtml(eyebrow)}</div>
        <h1>${escapeHtml(heading)}</h1>
        <p>${escapeHtml(body)}</p>
      </div>
      <div class="status">${escapeHtml(status)}</div>
      <div class="actions">
        <button class="primary" type="button" onclick="${actionScript}">重试连接</button>
        <button class="secondary" type="button" onclick="${openExternalScript}">浏览器打开</button>
      </div>
    </main>
  </body>
</html>`

  return `data:text/html;charset=UTF-8,${encodeURIComponent(html)}`
}

const showErrorShell = (mainWindow, details) => {
  const errorSummary = [
    rendererUrl,
    details?.errorCode ? `code=${details.errorCode}` : null,
    details?.errorDescription || null,
  ].filter(Boolean).join('\n')

  return mainWindow.loadURL(buildShellPageUrl({
    title: '连接失败',
    eyebrow: 'Desktop Recovery',
    heading: '页面入口暂时不可用',
    body: '桌面壳已经启动，但还没有连接上前端页面。请确认前端地址可访问，或直接点击重试。',
    status: errorSummary,
    tone: 'error',
  }))
}

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
    hosts: ['bilivideo.com', 'bilivideo.cn', 'bilibili.com', 'b23.tv', 'hdslb.com', 'acgvideo.com'],
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
      'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36',
    },
  },
  {
    hosts: ['youtube.com'],
    headers: {
      Referer: 'https://www.youtube.com/',
      Origin: 'https://www.youtube.com',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    },
  },
  {
    hosts: ['pornhub.com', 'phncdn.com'],
    headers: {
      Referer: 'https://www.pornhub.com/',
      Origin: 'https://www.pornhub.com',
      'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    },
  },
  {
    hosts: ['youporn.com', 'ypncdn.com'],
    headers: {
      Referer: 'https://www.youporn.com/',
      Origin: 'https://www.youporn.com',
      'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    },
  },
  {
    hosts: ['surrit.com'],
    headers: {
      Referer: 'https://missav.ai/',
      Origin: 'https://missav.ai',
      'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
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
  } catch {
    return null
  }
}

const shouldRelaxCrossOriginResponseHeaders = (targetUrl) => {
  try {
    const hostname = new URL(targetUrl).hostname.toLowerCase()
    return hostMatchesAnyRule(hostname, RELAXED_CROSS_ORIGIN_HOSTS)
  } catch {
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

const installDesktopMediaHeaders = () => {
  session.defaultSession.webRequest.onBeforeSendHeaders((details, callback) => {
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
    }).catch(() => {
      callback({ requestHeaders })
    })
  })

  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    if (!shouldRelaxCrossOriginResponseHeaders(details.url)) {
      callback({ responseHeaders: details.responseHeaders })
      return
    }

    callback({
      responseHeaders: stripRelaxedResponseHeaders(details.responseHeaders),
    })
  })
}

const isTrustedNavigation = (targetUrl) => {
  try {
    return new URL(targetUrl).origin === rendererOrigin
  } catch {
    return false
  }
}

const navigateToRenderer = async (mainWindow) => {
  try {
    await mainWindow.loadURL(rendererUrl)
  } catch (error) {
    console.error('[squirrel-desktop] Failed to load renderer', error)
    await showErrorShell(mainWindow, {
      errorDescription: error instanceof Error ? error.message : 'Unknown load error',
      errorCode: 'LOAD_URL_FAILED',
    })
  }
}

const reloadRenderer = (mainWindow, ignoreCache = false) => {
  if (mainWindow.isDestroyed()) {
    return
  }

  const currentUrl = mainWindow.webContents.getURL()
  if (!isTrustedNavigation(currentUrl)) {
    void navigateToRenderer(mainWindow)
    return
  }

  if (ignoreCache) {
    mainWindow.webContents.reloadIgnoringCache()
    return
  }

  mainWindow.webContents.reload()
}

const getDesktopWindowState = (mainWindow) => {
  return {
    isMaximized: mainWindow?.isMaximized() === true,
  }
}

const sendDesktopWindowState = (mainWindow) => {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return
  }

  mainWindow.webContents.send('desktop:window-state', getDesktopWindowState(mainWindow))
}

const installDesktopBridgeHandlers = () => {
  ipcMain.removeHandler('desktop:open-external')
  ipcMain.handle('desktop:open-external', async (_event, targetUrl) => {
    const normalizedUrl = String(targetUrl || '').trim()
    if (!normalizedUrl) {
      return false
    }

    await shell.openExternal(normalizedUrl)
    return true
  })

  ipcMain.removeHandler('desktop:resolve-youtube-playback')
  ipcMain.handle('desktop:resolve-youtube-playback', async (_event, targetUrl, options = {}) => {
    const normalizedUrl = normalizeTargetUrl(targetUrl)
    if (!normalizedUrl) {
      throw new Error('Invalid YouTube URL')
    }

    return resolveYouTubePlayback(normalizedUrl, {
      forceRefresh: options?.forceRefresh === true,
    })
  })

  ipcMain.removeHandler('desktop:resolve-youtube-subtitles')
  ipcMain.handle('desktop:resolve-youtube-subtitles', async (_event, targetUrl, options = {}) => {
    const normalizedUrl = normalizeTargetUrl(targetUrl)
    if (!normalizedUrl) {
      throw new Error('Invalid YouTube URL')
    }

    return resolveYouTubeSubtitles(normalizedUrl, {
      lang: String(options?.lang || '').trim(),
      format: String(options?.format || 'vtt').trim().toLowerCase(),
    })
  })

  ipcMain.removeHandler('desktop:resolve-bilibili-playback')
  ipcMain.handle('desktop:resolve-bilibili-playback', async (_event, targetUrl, options = {}) => {
    const normalizedUrl = normalizeTargetUrl(targetUrl)
    if (!normalizedUrl) {
      throw new Error('Invalid Bilibili URL')
    }

    const cookie = await buildCookieHeaderForUrl(normalizedUrl)
    return resolveBilibiliPlayback(normalizedUrl, {
      cookie,
      forceRefresh: options?.forceRefresh === true,
      fetchImpl: createSessionFetch(),
    })
  })

  ipcMain.removeHandler('desktop:resolve-pornhub-playback')
  ipcMain.handle('desktop:resolve-pornhub-playback', async (_event, targetUrl, options = {}) => {
    const normalizedUrl = normalizeTargetUrl(targetUrl)
    if (!normalizedUrl) {
      throw new Error('Invalid Pornhub URL')
    }

    const cookie = await buildCookieHeaderForUrl(normalizedUrl)
    return resolvePornhubPlayback(normalizedUrl, {
      cookie,
      fetchImpl: createSessionFetch(),
      forceRefresh: options?.forceRefresh === true,
    })
  })

  ipcMain.removeHandler('desktop:resolve-youporn-playback')
  ipcMain.handle('desktop:resolve-youporn-playback', async (_event, targetUrl, options = {}) => {
    const normalizedUrl = normalizeTargetUrl(targetUrl)
    if (!normalizedUrl) {
      throw new Error('Invalid YouPorn URL')
    }

    const cookie = await buildCookieHeaderForUrl(normalizedUrl)
    return resolveYouPornPlayback(normalizedUrl, {
      cookie,
      fetchImpl: createSessionFetch(),
      forceRefresh: options?.forceRefresh === true,
    })
  })

  ipcMain.removeHandler('desktop:search-remote-videos')
  ipcMain.handle('desktop:search-remote-videos', async (_event, options = {}) => {
    return searchRemoteVideos({
      query: options?.query,
      site: options?.site || 'all',
      limit: options?.limit || 20,
      page: options?.page || 1,
      fetchImpl: createSessionFetch(),
      buildCookieHeader: buildCookieHeaderForUrl,
      loadDocumentHtml: loadDocumentHtmlWithBrowserWindow,
    })
  })

  ipcMain.removeHandler('desktop:get-site-login-status')
  ipcMain.handle('desktop:get-site-login-status', async (_event, siteName) => {
    return buildDesktopSiteLoginStatus(siteName)
  })

  ipcMain.removeHandler('desktop:open-site-login')
  ipcMain.handle('desktop:open-site-login', async (event, siteName) => {
    return openDesktopSiteLoginWindow(siteName, BrowserWindow.fromWebContents(event.sender))
  })

  ipcMain.removeHandler('desktop:clear-site-session')
  ipcMain.handle('desktop:clear-site-session', async (_event, siteName) => {
    return clearDesktopSiteSession(siteName)
  })

  ipcMain.removeAllListeners('desktop:reload')
  ipcMain.on('desktop:reload', (event) => {
    const mainWindow = BrowserWindow.fromWebContents(event.sender)
    if (!mainWindow) {
      return
    }

    reloadRenderer(mainWindow)
  })

  ipcMain.removeHandler('desktop:get-window-state')
  ipcMain.handle('desktop:get-window-state', (event) => {
    const mainWindow = BrowserWindow.fromWebContents(event.sender)
    if (!mainWindow) {
      return { isMaximized: false }
    }

    return getDesktopWindowState(mainWindow)
  })

  ipcMain.removeHandler('desktop:window-action')
  ipcMain.handle('desktop:window-action', (event, action) => {
    const mainWindow = BrowserWindow.fromWebContents(event.sender)
    if (!mainWindow) {
      return { isMaximized: false }
    }

    switch (String(action || '')) {
      case 'minimize':
        mainWindow.minimize()
        break
      case 'toggle-maximize':
        if (mainWindow.isMaximized()) {
          mainWindow.unmaximize()
        } else {
          mainWindow.maximize()
        }
        break
      case 'close':
        mainWindow.close()
        break
      default:
        break
    }

    return getDesktopWindowState(mainWindow)
  })

  // Server config IPC
  ipcMain.removeHandler('server:get-url')
  ipcMain.handle('server:get-url', () => {
    return loadServerConfig()
  })

  ipcMain.removeHandler('server:set-url')
  ipcMain.handle('server:set-url', (_event, url) => {
    const normalized = String(url || '').trim()
    if (!normalized) return false

    try {
      const parsed = new URL(normalized)
      if (!['http:', 'https:'].includes(parsed.protocol)) return false
      const finalUrl = parsed.origin
      const ok = saveServerConfig(finalUrl)

      if (ok) {
        // Broadcast change to all windows
        BrowserWindow.getAllWindows().forEach((win) => {
          if (!win.isDestroyed()) {
            win.webContents.send('server:url-changed', finalUrl)
          }
        })
      }

      return ok ? finalUrl : false
    } catch {
      return false
    }
  })

  ipcMain.removeHandler('server:clear-url')
  ipcMain.handle('server:clear-url', () => {
    try {
      fs.rmSync(getServerConfigPath())
    } catch {
      // ignore
    }

    BrowserWindow.getAllWindows().forEach((win) => {
      if (!win.isDestroyed()) {
        win.webContents.send('server:url-changed', '')
      }
    })

    return true
  })
}

const buildContextMenuTemplate = (mainWindow, params) => {
  const template = []

  if (params.linkURL) {
    template.push(
      {
        label: '在浏览器中打开链接',
        click: () => {
          void shell.openExternal(params.linkURL)
        },
      },
      {
        label: '复制链接地址',
        click: () => clipboard.writeText(params.linkURL),
      },
      { type: 'separator' },
    )
  }

  if (params.isEditable) {
    template.push(
      { role: 'undo', label: '撤销' },
      { role: 'redo', label: '重做' },
      { type: 'separator' },
      { role: 'cut', label: '剪切' },
      { role: 'copy', label: '复制' },
      { role: 'paste', label: '粘贴' },
      { role: 'selectAll', label: '全选' },
    )
  } else if (String(params.selectionText || '').trim()) {
    template.push(
      { role: 'copy', label: '复制' },
      { role: 'selectAll', label: '全选' },
    )
  }

  template.push(
    { type: 'separator' },
    {
      label: '后退',
      enabled: mainWindow.webContents.canGoBack(),
      click: () => mainWindow.webContents.goBack(),
    },
    {
      label: '前进',
      enabled: mainWindow.webContents.canGoForward(),
      click: () => mainWindow.webContents.goForward(),
    },
    {
      label: '重新加载',
      click: () => reloadRenderer(mainWindow),
    },
  )

  if (!app.isPackaged) {
    template.push(
      { type: 'separator' },
      {
        label: '检查元素',
        click: () => mainWindow.webContents.inspectElement(params.x, params.y),
      },
    )
  }

  return template
}

const installMainWindowBehaviors = (mainWindow) => {
  const syncDesktopWindowState = () => {
    sendDesktopWindowState(mainWindow)
  }

  mainWindow.on('page-title-updated', (event, title) => {
    event.preventDefault()
    mainWindow.setTitle(formatWindowTitle(title))
  })

  mainWindow.on('maximize', syncDesktopWindowState)
  mainWindow.on('unmaximize', syncDesktopWindowState)
  mainWindow.webContents.on('did-finish-load', () => {
    syncDesktopWindowState()
  })

  mainWindow.webContents.on('before-input-event', (event, input) => {
    const key = String(input.key || '').toLowerCase()
    const isPrimaryModifier = input.control || input.meta
    const openDevTools =
      key === 'f12'
      || (isPrimaryModifier && input.shift && key === 'i')
      || (input.meta && input.alt && key === 'i')

    const reloadPage =
      key === 'f5'
      || (isPrimaryModifier && key === 'r')

    if (input.type !== 'keyDown') {
      return
    }

    if (reloadPage) {
      event.preventDefault()
      reloadRenderer(mainWindow, input.shift === true)
      return
    }

    if (!openDevTools) {
      return
    }

    event.preventDefault()
    if (mainWindow.webContents.isDevToolsOpened()) {
      mainWindow.webContents.closeDevTools()
      return
    }

    mainWindow.webContents.openDevTools({ mode: 'detach' })
  })

  mainWindow.webContents.on('context-menu', (event, params) => {
    const menu = Menu.buildFromTemplate(buildContextMenuTemplate(mainWindow, params))
    if (menu.items.length > 0) {
      menu.popup({ window: mainWindow })
    }
  })

  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL, isMainFrame) => {
    if (!isMainFrame || errorCode === -3 || String(validatedURL || '').startsWith('data:')) {
      return
    }

    void showErrorShell(mainWindow, { errorCode, errorDescription })
  })

  mainWindow.webContents.on('render-process-gone', (_event, details) => {
    void showErrorShell(mainWindow, {
      errorCode: details.reason,
      errorDescription: 'Renderer process exited unexpectedly',
    })
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (isTrustedNavigation(url)) {
      return { action: 'allow' }
    }

    void shell.openExternal(url)
    return { action: 'deny' }
  })

  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (isTrustedNavigation(url)) {
      return
    }

    event.preventDefault()
    void shell.openExternal(url)
  })
}

const createMainWindow = () => {
  const windowState = loadWindowState()
  const isMac = process.platform === 'darwin'
  const mainWindow = new BrowserWindow({
    x: windowState.x,
    y: windowState.y,
    width: windowState.width,
    height: windowState.height,
    minWidth: DEFAULT_WINDOW_STATE.minWidth,
    minHeight: DEFAULT_WINDOW_STATE.minHeight,
    show: false,
    title: APP_NAME,
    autoHideMenuBar: true,
    backgroundColor: '#091019',
    ...(isMac
      ? {
          titleBarStyle: 'hiddenInset',
        }
      : {
          frame: false,
          titleBarStyle: 'hidden',
        }),
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      // Desktop playback pulls media directly from site CDNs, so the shell
      // must not enforce browser CORS for those cross-origin segment requests.
      webSecurity: false,
    },
  })

  bindWindowStatePersistence(mainWindow)
  installMainWindowBehaviors(mainWindow)

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })

  if (windowState.isMaximized) {
    mainWindow.maximize()
  }

  void navigateToRenderer(mainWindow)
  return mainWindow
}

const hasSingleInstanceLock = app.requestSingleInstanceLock()

if (!hasSingleInstanceLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    const mainWindow = BrowserWindow.getAllWindows()[0]
    if (!mainWindow) {
      return
    }

    if (mainWindow.isMinimized()) {
      mainWindow.restore()
    }
    if (!mainWindow.isVisible()) {
      mainWindow.show()
    }

    mainWindow.focus()
    if (!isTrustedNavigation(mainWindow.webContents.getURL())) {
      reloadRenderer(mainWindow)
    }
  })

  app.whenReady().then(() => {
    installDesktopBridgeHandlers()
    installDesktopMediaHeaders()
    createMainWindow()
    prewarmDesktopPlaybackProviders()

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        createMainWindow()
        return
      }

      const mainWindow = BrowserWindow.getAllWindows()[0]
      if (mainWindow?.isMinimized()) {
        mainWindow.restore()
      }
      mainWindow?.focus()
    })
  })
}

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
