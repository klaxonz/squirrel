import { BrowserWindow, session } from 'electron'
import { clearBilibiliPlaybackCache } from './playback/providers/bilibili/index.mjs'
import { resolveYouTubeOAuthRevoke, resolveYouTubeOAuthSetup, resolveYouTubeOAuthStatus } from './playback/providers/youtube/index.mjs'
import {
  normalizeTargetUrl,
  mergeCookieHeaders,
  readPornhubCookieFileHeader,
  readYouPornCookieFileHeader,
  isJavdbCookieTarget,
  isBilibiliCookieTarget,
  isPornhubCookieTarget,
  isYouPornCookieTarget,
} from './cookie-header.mjs'
import {
  APP_NAME,
  desktopChromeUserAgent,
  desktopChromeUserAgentMetadata,
  desktopChromeAcceptLanguage,
  SITE_SESSION_STORAGE_TYPES,
  javdbOrigin,
  javdbReferer,
  javdbLoginCheckUrl,
  javdbLoginRedirectPattern,
  javdbLoginPagePattern,
  javdbErrorPagePattern,
  pornhubOrigin,
  pornhubReferer,
  youpornOrigin,
  youpornReferer,
  pornhubAgeGateCookieHeader,
  youpornAgeGateCookieHeader,
  pornhubLoggedInPattern,
  pornhubLoggedOutPattern,
  pornhubUsernamePattern,
  pornhubDataUsernamePattern,
  pornhubProfileLinkPattern,
  pornhubProfileBlockPattern,
  pornhubProfileStatusPattern,
  youpornLoggedInPattern,
  youpornLoggedOutPattern,
  youpornUsernamePattern,
  youpornProfileLinkPattern,
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
  },
  javdb: {
    label: 'JavDB',
    loginUrl: 'https://javdb.com/users/sign_in',
    userAgent: desktopChromeUserAgent,
    userAgentMetadata: desktopChromeUserAgentMetadata,
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

export const getSiteLoginProfile = (siteName) => {
  const normalizedSite = normalizeSiteName(siteName)
  return SITE_LOGIN_PROFILES[normalizedSite] ? { siteName: normalizedSite, ...SITE_LOGIN_PROFILES[normalizedSite] } : null
}

export const getCookieProfileForUrl = (targetUrl) => {
  if (isJavdbCookieTarget(targetUrl)) return getSiteLoginProfile('javdb')
  if (isBilibiliCookieTarget(targetUrl)) return getSiteLoginProfile('bilibili')
  if (isPornhubCookieTarget(targetUrl)) return getSiteLoginProfile('pornhub')
  if (isYouPornCookieTarget(targetUrl)) return getSiteLoginProfile('youporn')
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

const buildCookieHeaderFromCookies = (cookies) => {
  return cookies.map((cookie) => `${cookie.name}=${cookie.value}`).join('; ')
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

export const buildCookieHeaderForUrl = async (targetUrl) => {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    return ''
  }

  const sessionCookieHeader = await buildSessionCookieHeaderForUrl(normalizedUrl)

  if (isJavdbCookieTarget(normalizedUrl)) {
    return sessionCookieHeader
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
  const cookieHeader = buildCookieHeaderFromCookies(cookies)
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

const extractYouPornDesktopUsername = (body) => {
  const match = youpornUsernamePattern.exec(body) || youpornProfileLinkPattern.exec(body)
  const username = String(match?.[1] || '').trim()
  return username || null
}

const checkYouPornDesktopPageLogin = async (cookieHeader) => {
  const response = await session.defaultSession.fetch(youpornReferer, {
    headers: {
      'Accept-Language': 'en-US,en;q=0.9',
      Origin: youpornOrigin,
      Referer: youpornReferer,
      'User-Agent': desktopChromeUserAgent,
      Cookie: cookieHeader,
    },
    redirect: 'follow',
  })
  const body = await response.text()
  const finalUrl = response.url || youpornReferer

  if (response.status === 401) {
    return { logged_in: false, message: `被拒绝访问 (status=${response.status})` }
  }
  if ([403, 429, 500, 502, 503, 504].includes(response.status)) {
    return { logged_in: false, message: `检测失败: 被拒绝访问 (status=${response.status})` }
  }
  if (finalUrl.includes('/login')) {
    return { logged_in: false, message: '被重定向到登录页' }
  }

  const username = extractYouPornDesktopUsername(body)
  if (youpornLoggedInPattern.test(body)) {
    return { logged_in: true, username, message: '桌面会话有效' }
  }
  if (youpornLoggedOutPattern.test(body)) {
    return { logged_in: false, message: '未登录' }
  }

  return {
    logged_in: false,
    message: '未检测到登录标记',
  }
}

const buildYouPornDesktopLoginStatus = async (profile, cookies) => {
  const cookieHeader = buildCookieHeaderFromCookies(cookies)
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
    const status = await checkYouPornDesktopPageLogin(mergeCookieHeaders(youpornAgeGateCookieHeader, cookieHeader))
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

const buildYouPornLoginWindowStatus = async (profile, loginWindow) => {
  if (!loginWindow || loginWindow.isDestroyed() || loginWindow.webContents.isLoading()) {
    return null
  }

  const normalizedUrl = normalizeTargetUrl(loginWindow.webContents.getURL())
  if (!normalizedUrl || !hostMatchesLoginProfile(new URL(normalizedUrl).hostname, profile.allowedHosts)) {
    return null
  }

  let status = null
  try {
    status = await loginWindow.webContents.executeJavaScript(`(() => {
      const pageParams = window.page_params || {}
      const pageUsername = typeof pageParams.liu_username === 'string' ? pageParams.liu_username.trim() : ''
      const profileLink = document.querySelector('#js_mainMenu .user-item a[href^="/users/"]')
      const logoutLink = document.querySelector('#js_mainMenu a[href^="/logout"]')
      const signedOutLink = document.querySelector('#js_signupLink, #upgrade-menujs_loginLink')
      const profileHref = profileLink ? profileLink.getAttribute('href') || '' : ''
      const linkUsername = profileHref.match(/^\\/users\\/([^/?#]+)/)?.[1] || ''
      const loggedIn = pageParams.isLoggedInUser === true
        || Boolean(pageParams.liu)
        || Boolean((profileLink || logoutLink) && !signedOutLink)

      return {
        logged_in: loggedIn,
        username: pageUsername || linkUsername || null,
      }
    })()`, true)
  } catch {
    return null
  }

  if (!status?.logged_in) {
    return null
  }

  const cookies = await getDesktopSiteCookies(profile)
  return {
    site_name: profile.siteName,
    supported: true,
    logged_in: true,
    username: status.username || null,
    message: '桌面会话有效',
    checked_at: new Date().toISOString(),
    source: 'desktop',
    cookie_count: cookies.length,
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
  if (profile.siteName === 'javdb') {
    return buildJavdbDesktopLoginStatus(profile, cookies)
  }
  if (profile.siteName === 'pornhub') {
    return buildPornhubDesktopLoginStatus(profile, cookies)
  }
  if (profile.siteName === 'youporn') {
    return buildYouPornDesktopLoginStatus(profile, cookies)
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
      || profile.siteName === 'youporn'
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
      if (profile.siteName === 'youporn') {
        buildYouPornLoginWindowStatus(profile, loginWindow)
          .then((status) => {
            if (!status?.logged_in) return buildDesktopSiteLoginStatus(profile.siteName)
            return status
          })
          .then((status) => {
            if (!status.logged_in) return
            if (!loginWindow.isDestroyed()) {
              loginWindow.close()
            }
            resolveWithStatus(status)
          })
          .catch(reject)
        return
      }

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
