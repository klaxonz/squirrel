import fs from 'node:fs'
import path from 'node:path'
import { pathToFileURL } from 'node:url'
import { app, BrowserWindow } from 'electron'
import { prewarmPlaybackProviders } from './playback/providers/index.mjs'
import { installDesktopBridgeHandlers } from './ipc-handlers.mjs'
import { installDesktopMediaHeaders } from './media-headers.mjs'
import { createMainWindow, ensureRendererLoaded, setRendererOrigin } from './window.mjs'
import { setRendererUrl } from './shell-pages.mjs'
import { closeCamoufoxDocumentLoader } from './document-loader.mjs'
import { __dirname } from './constants.mjs'

const DEFAULT_DEV_RENDERER_URL = 'http://127.0.0.1:5173/'

const resolvePackagedRendererUrl = () => {
  const indexHtml = path.join(__dirname, '..', 'renderer', 'dist', 'index.html')
  return pathToFileURL(indexHtml).href
}

const resolveRendererUrl = () => {
  const envValue = String(process.env.DESKTOP_RENDERER_URL || '').trim()
  if (envValue) {
    try {
      return new URL(envValue).toString()
    } catch {
      // Fall through to packaged / default resolution.
    }
  }

  // Dev always passes DESKTOP_RENDERER_URL (Vite). Packaged builds load local dist.
  if (app.isPackaged) {
    return resolvePackagedRendererUrl()
  }

  // Unpackaged `electron .` without env: prefer built renderer if present, else Vite default.
  const builtIndex = path.join(__dirname, '..', 'renderer', 'dist', 'index.html')
  if (fs.existsSync(builtIndex)) {
    return pathToFileURL(builtIndex).href
  }

  return DEFAULT_DEV_RENDERER_URL
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
  setTimeout(() => {
    prewarmPlaybackProviders()
  }, 1000)
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
    installDesktopBridgeHandlers()
    const cleanupMediaHeaders = installDesktopMediaHeaders()
    app.on('will-quit', cleanupMediaHeaders)
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
  void closeCamoufoxDocumentLoader()
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
