import { BrowserWindow, ipcMain, session, shell } from 'electron'
import { reloadRenderer, getDesktopWindowState } from './window.mjs'
import {
  createWebContentOpener,
  normalizeWebContentUrl,
} from './web-content-window.mjs'

const webContentOpener = createWebContentOpener({
  createWindow: (options) => new BrowserWindow(options),
  openExternal: (targetUrl) => shell.openExternal(targetUrl),
  sessionManager: session,
})

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
    const parentWindow = BrowserWindow.fromWebContents(event.sender)
    return webContentOpener.openWebContent(targetUrl, parentWindow)
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
