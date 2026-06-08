import fs from 'node:fs'
import path from 'node:path'
import { app, BrowserWindow, ipcMain } from 'electron'
import { SERVER_CONFIG_FILE } from './constants.mjs'

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
        console.debug('[squirrel-desktop] ipc-server-config: loadServerConfig invalid URL', url)
        return ''
      }
    }
    return ''
  } catch {
    console.debug('[squirrel-desktop] ipc-server-config: loadServerConfig read/parse failed', getServerConfigPath())
    return ''
  }
}

const saveServerConfig = (url) => {
  try {
    fs.mkdirSync(path.dirname(getServerConfigPath()), { recursive: true })
    fs.writeFileSync(getServerConfigPath(), JSON.stringify({ serverUrl: url }, null, 2), 'utf8')
    return true
  } catch {
    console.error('[squirrel-desktop] ipc-server-config: saveServerConfig failed', getServerConfigPath())
    return false
  }
}

export const installServerConfigHandlers = () => {
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
        BrowserWindow.getAllWindows().forEach((win) => {
          if (!win.isDestroyed()) {
            win.webContents.send('server:url-changed', finalUrl)
          }
        })
      }

      return ok ? finalUrl : false
    } catch {
      console.debug('[squirrel-desktop] ipc-server-config: server:set-url invalid URL', normalized)
      return false
    }
  })

  ipcMain.removeHandler('server:clear-url')
  ipcMain.handle('server:clear-url', () => {
    try {
      fs.rmSync(getServerConfigPath())
    } catch {
      console.debug('[squirrel-desktop] ipc-server-config: server:clear-url no config to remove')
    }

    BrowserWindow.getAllWindows().forEach((win) => {
      if (!win.isDestroyed()) {
        win.webContents.send('server:url-changed', '')
      }
    })

    return true
  })
}
