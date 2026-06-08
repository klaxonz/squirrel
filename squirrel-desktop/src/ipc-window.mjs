import { BrowserWindow, ipcMain, shell } from 'electron'
import { reloadRenderer, getDesktopWindowState } from './window.mjs'

export const installWindowHandlers = () => {
  ipcMain.removeHandler('desktop:open-external')
  ipcMain.handle('desktop:open-external', async (_event, targetUrl) => {
    const normalizedUrl = String(targetUrl || '').trim()
    if (!normalizedUrl) {
      return false
    }

    let parsed
    try {
      parsed = new URL(normalizedUrl)
    } catch {
      return false
    }

    if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') {
      return false
    }

    await shell.openExternal(normalizedUrl)
    return true
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
