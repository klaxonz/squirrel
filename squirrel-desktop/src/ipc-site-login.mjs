import { BrowserWindow, ipcMain } from 'electron'
import { buildDesktopSiteLoginStatus, openDesktopSiteLoginWindow, clearDesktopSiteSession } from './site-login.mjs'

export const installSiteLoginHandlers = () => {
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
}
