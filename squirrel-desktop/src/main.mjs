import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { app, BrowserWindow, clipboard, ipcMain, Menu, session, shell } from 'electron'
import { resolveBilibiliPlayback } from './playback/providers/bilibili/index.mjs'
import { resolveYouTubePlayback } from './playback/providers/youtube/index.mjs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const repoRoot = path.resolve(__dirname, '..', '..')
const bilibiliCookieFilePath = path.join(repoRoot, 'config', 'site_cookies', 'bilibili.txt')
const youtubeCookieFilePath = path.join(repoRoot, 'config', 'site_cookies', 'youtube.txt')
const youtubeOAuthStateFilePath = path.join(repoRoot, 'config', 'youtube_oauth.json')

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

const isYouTubeCookieTarget = (targetUrl) => {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    return false
  }

  try {
    const hostname = new URL(normalizedUrl).hostname.toLowerCase()
    return hostname === 'youtube.com'
      || hostname.endsWith('.youtube.com')
      || hostname === 'youtu.be'
      || hostname.endsWith('.googlevideo.com')
      || hostname.endsWith('.gvt1.com')
      || hostname.endsWith('.ytimg.com')
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

const readYoutubeCookieFileHeader = () => {
  return readNetscapeCookieFileHeader(youtubeCookieFilePath, ['youtube.com'])
}

const readBilibiliCookieFileHeader = () => {
  return readNetscapeCookieFileHeader(bilibiliCookieFilePath, [
    'bilibili.com',
    'bilivideo.com',
    'bilivideo.cn',
    'hdslb.com',
    'acgvideo.com',
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

const buildCookieHeaderForUrl = async (targetUrl) => {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    return ''
  }

  let sessionCookieHeader = ''
  try {
    const cookies = await session.defaultSession.cookies.get({ url: normalizedUrl })
    if (Array.isArray(cookies) && cookies.length > 0) {
      sessionCookieHeader = cookies
        .map((cookie) => `${cookie.name}=${cookie.value}`)
        .join('; ')
    }
  } catch {
    sessionCookieHeader = ''
  }

  if (isYouTubeCookieTarget(normalizedUrl)) {
    return mergeCookieHeaders(readYoutubeCookieFileHeader(), sessionCookieHeader)
  }

  if (isBilibiliCookieTarget(normalizedUrl)) {
    return mergeCookieHeaders(readBilibiliCookieFileHeader(), sessionCookieHeader)
  }

  return sessionCookieHeader
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
    hosts: ['bilivideo.com', 'bilivideo.cn', 'bilibili.com', 'b23.tv', 'hdslb.com', 'acgvideo.com'],
    headers: {
      Referer: 'https://www.bilibili.com/',
      Origin: 'https://www.bilibili.com',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
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
      'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    },
  },
]

const RELAXED_CROSS_ORIGIN_HOSTS = [
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
    callback({ requestHeaders })
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

    const cookie = await buildCookieHeaderForUrl(normalizedUrl)
    return resolveYouTubePlayback(normalizedUrl, {
      cookie,
      forceRefresh: options?.forceRefresh === true,
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
    })
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

  const debugDesktopChrome = async () => {
    if (app.isPackaged) {
      return
    }

    try {
      const debugState = await mainWindow.webContents.executeJavaScript(`(() => ({
        hasDesktopApp: Boolean(window.desktopApp),
        desktopAppKeys: Object.keys(window.desktopApp || {}),
        isDesktopShell: Boolean(window.desktopApp?.isDesktop),
        titlebarExists: Boolean(document.querySelector('.desktop-titlebar')),
        controlsExists: Boolean(document.querySelector('.desktop-window-controls')),
        titlebarText: document.querySelector('.desktop-titlebar')?.innerText || '',
      }))()`, true)
      console.log('[squirrel-desktop] Chrome debug', debugState)
    } catch (error) {
      console.error('[squirrel-desktop] Failed to inspect desktop chrome', error)
    }
  }

  mainWindow.on('page-title-updated', (event, title) => {
    event.preventDefault()
    mainWindow.setTitle(formatWindowTitle(title))
  })

  mainWindow.on('maximize', syncDesktopWindowState)
  mainWindow.on('unmaximize', syncDesktopWindowState)
  mainWindow.webContents.on('did-finish-load', () => {
    syncDesktopWindowState()
    void debugDesktopChrome()
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
