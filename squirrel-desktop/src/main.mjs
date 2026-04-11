import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { app, BrowserWindow, session, shell } from 'electron'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const DEFAULT_APP_URL = 'http://127.0.0.1:8001'

const resolveRendererUrl = () => {
  const value = String(
    process.env.DESKTOP_RENDERER_URL
    || process.env.DESKTOP_APP_URL
    || DEFAULT_APP_URL
  ).trim()

  return value || DEFAULT_APP_URL
}

const rendererUrl = resolveRendererUrl()
const rendererOrigin = new URL(rendererUrl).origin

const MEDIA_HEADER_RULES = [
  {
    hosts: ['bilivideo.com', 'bilibili.com', 'b23.tv'],
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
]

const matchMediaHeaderRule = (targetUrl) => {
  try {
    const hostname = new URL(targetUrl).hostname.toLowerCase()
    return MEDIA_HEADER_RULES.find((rule) => {
      return rule.hosts.some((host) => hostname === host || hostname.endsWith(`.${host}`))
    }) || null
  } catch {
    return null
  }
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
}

const isTrustedNavigation = (targetUrl) => {
  try {
    return new URL(targetUrl).origin === rendererOrigin
  } catch {
    return false
  }
}

const createMainWindow = () => {
  const mainWindow = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 1100,
    minHeight: 720,
    show: false,
    autoHideMenuBar: true,
    backgroundColor: '#101418',
    webPreferences: {
      preload: path.join(__dirname, 'preload.mjs'),
      contextIsolation: true,
      nodeIntegration: false,
      // Desktop playback pulls media directly from site CDNs, so the shell
      // must not enforce browser CORS for those cross-origin segment requests.
      webSecurity: false,
    },
  })

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })

  mainWindow.webContents.on('before-input-event', (event, input) => {
    const key = String(input.key || '').toLowerCase()
    const openDevTools =
      key === 'f12'
      || ((input.control || input.meta) && input.shift && key === 'i')
      || (input.meta && input.alt && key === 'i')

    if (!openDevTools || input.type !== 'keyDown') {
      return
    }

    event.preventDefault()
    if (mainWindow.webContents.isDevToolsOpened()) {
      mainWindow.webContents.closeDevTools()
      return
    }

    mainWindow.webContents.openDevTools({ mode: 'detach' })
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

  void mainWindow.loadURL(rendererUrl)
  return mainWindow
}

app.whenReady().then(() => {
  installDesktopMediaHeaders()
  createMainWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
