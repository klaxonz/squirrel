import { BrowserWindow, ipcMain, net, session, shell, WebContentsView } from 'electron'
import { reloadRenderer, getDesktopWindowState } from './window.mjs'
import { createInAppWebViewController } from './in-app-web-view.mjs'
import {
  createWebContentOpener,
  normalizeWebContentUrl,
  probeFrameEmbeddability,
} from './web-content-window.mjs'

const webContentOpener = createWebContentOpener({
  createWindow: (options) => new BrowserWindow(options),
  openExternal: (targetUrl) => shell.openExternal(targetUrl),
  sessionManager: session,
})

const inAppWebView = createInAppWebViewController({
  createWebContentsView: (options) => new WebContentsView(options),
  openExternal: (targetUrl) => shell.openExternal(targetUrl),
  sessionManager: session,
})

const desktopFetch = (...args) => {
  if (typeof net?.fetch === 'function') return net.fetch(...args)
  return globalThis.fetch(...args)
}

const parentWindowFromEvent = (event) => BrowserWindow.fromWebContents(event.sender)

export const installWindowHandlers = () => {
  ipcMain.removeHandler('desktop:open-external')
  ipcMain.handle('desktop:open-external', async (_event, targetUrl) => {
    const normalizedUrl = normalizeWebContentUrl(targetUrl)
    if (!normalizedUrl) {
      return false
    }

    await shell.openExternal(normalizedUrl)
    return true
  })

  ipcMain.removeHandler('desktop:open-web-content')
  ipcMain.handle('desktop:open-web-content', (event, targetUrl) => {
    const parentWindow = parentWindowFromEvent(event)
    return webContentOpener.openWebContent(targetUrl, parentWindow)
  })

  ipcMain.removeHandler('desktop:probe-frame-embeddability')
  ipcMain.handle('desktop:probe-frame-embeddability', async (_event, targetUrl) => {
    return probeFrameEmbeddability(targetUrl, { fetchImpl: desktopFetch })
  })

  ipcMain.removeHandler('desktop:in-app-web-view-open')
  ipcMain.handle('desktop:in-app-web-view-open', async (event, payload = {}) => {
    const parentWindow = parentWindowFromEvent(event)
    if (!parentWindow) return false
    return inAppWebView.open(parentWindow, payload?.url, payload?.bounds)
  })

  ipcMain.removeHandler('desktop:in-app-web-view-set-bounds')
  ipcMain.handle('desktop:in-app-web-view-set-bounds', (event, bounds) => {
    const parentWindow = parentWindowFromEvent(event)
    if (!parentWindow) return false
    return inAppWebView.setBounds(parentWindow, bounds)
  })

  ipcMain.removeHandler('desktop:in-app-web-view-reload')
  ipcMain.handle('desktop:in-app-web-view-reload', async (event) => {
    const parentWindow = parentWindowFromEvent(event)
    if (!parentWindow) return false
    return inAppWebView.reload(parentWindow)
  })

  ipcMain.removeHandler('desktop:in-app-web-view-hide')
  ipcMain.handle('desktop:in-app-web-view-hide', (event) => {
    const parentWindow = parentWindowFromEvent(event)
    return inAppWebView.hide(parentWindow)
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
}
