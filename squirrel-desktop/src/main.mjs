import { app, BrowserWindow } from 'electron'
import { prewarmPlaybackProviders } from './playback/providers/index.mjs'
import { installDesktopBridgeHandlers } from './ipc-handlers.mjs'
import { installDesktopMediaHeaders } from './media-headers.mjs'
import { createMainWindow, setRendererOrigin } from './window.mjs'
import { setRendererUrl } from './shell-pages.mjs'
import { closeCamoufoxDocumentLoader } from './document-loader.mjs'
import { DEFAULT_APP_URL } from './constants.mjs'

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
    if (new URL(mainWindow.webContents.getURL()).origin !== rendererOrigin) {
      mainWindow.loadURL(rendererUrl)
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
