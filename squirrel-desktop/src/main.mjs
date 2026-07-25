import path from 'node:path'
import { pathToFileURL } from 'node:url'
import { app, BrowserWindow } from 'electron'
import { prewarmPlaybackProviders } from './playback/providers/index.mjs'
import { installDesktopBridgeHandlers } from './ipc-handlers.mjs'
import { installDesktopMediaHeaders, installDesktopSessionUserAgent } from './media-headers.mjs'
import { createMainWindow, ensureRendererLoaded, setRendererOrigin } from './window.mjs'
import { setRendererUrl } from './shell-pages.mjs'
import { APP_ICON_PATH, APP_ID, __dirname, youtubeOAuthStateFilePath } from './constants.mjs'
import { resolveDesktopRendererUrl } from './renderer-url.mjs'

// Ensure YouTube TV OAuth state resolves even when the process launcher does
// not inject YOUTUBE_OAUTH_STATE_FILE (common for `npm run dev:desktop`).
if (!String(process.env.YOUTUBE_OAUTH_STATE_FILE || '').trim()) {
  process.env.YOUTUBE_OAUTH_STATE_FILE = youtubeOAuthStateFilePath
}

const DEFAULT_DEV_RENDERER_URL = 'http://127.0.0.1:5174/'

const resolvePackagedRendererUrl = () => {
  const indexHtml = path.join(__dirname, '..', 'renderer', 'dist', 'index.html')
  return pathToFileURL(indexHtml).href
}

const resolveRendererUrl = () => {
  return resolveDesktopRendererUrl({
    configuredUrl: process.env.DESKTOP_RENDERER_URL,
    isPackaged: app.isPackaged,
    packagedRendererUrl: resolvePackagedRendererUrl(),
    devRendererUrl: DEFAULT_DEV_RENDERER_URL,
  })
}

const rendererUrl = resolveRendererUrl()
let rendererOrigin = ''
try {
  rendererOrigin = new URL(rendererUrl).origin
} catch {
  rendererOrigin = 'file://'
}

setRendererUrl(rendererUrl)
setRendererOrigin(rendererUrl, rendererOrigin)

const prewarmDesktopPlaybackProviders = () => {
  // Start as soon as the main process is ready. The previous 1s delay left the
  // first click cold for remote WEB session + BotGuard minter (~1–6s), which
  // dominated YouTube start latency.
  prewarmPlaybackProviders()
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
    // Use the same loadFile/loadURL path as first launch (not raw loadURL).
    ensureRendererLoaded(mainWindow)
  })

  app.whenReady().then(() => {
    if (process.platform === 'win32') {
      app.setAppUserModelId(APP_ID)
    } else if (process.platform === 'darwin') {
      app.dock.setIcon(APP_ICON_PATH)
    }

    installDesktopBridgeHandlers()
    // FreeTube: strip Electron from session UA before any googlevideo traffic.
    installDesktopSessionUserAgent()
    const cleanupMediaHeaders = installDesktopMediaHeaders()
    app.on('will-quit', cleanupMediaHeaders)
    // Prewarm before createMainWindow so BotGuard + WEB session start while
    // the renderer boots — first click more often hits a warm minter.
    prewarmDesktopPlaybackProviders()
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

app.on('child-process-gone', (_event, details) => {
  console.error('[squirrel-desktop] Child process gone', {
    type: details?.type,
    reason: details?.reason,
    exitCode: details?.exitCode,
    serviceName: details?.serviceName,
    name: details?.name,
  })
})
