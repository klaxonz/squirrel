import fs from 'node:fs'
import path from 'node:path'
import { app, BrowserWindow, ipcMain, shell } from 'electron'
import { resolveBilibiliPlayback, resolveBilibiliSubtitles } from './playback/providers/bilibili/index.mjs'
import { resolveJavdbMetadata, resolveJavdbPlayback } from './playback/providers/javdb/index.mjs'
import { resolvePornhubPlayback } from './playback/providers/pornhub/index.mjs'
import { resolveYouPornPlayback } from './playback/providers/youporn/index.mjs'
import { resolveYouTubePlayback, resolveYouTubeSubtitles } from './playback/providers/youtube/index.mjs'
import { getRemoteChannel } from './search/providers/remote-channel.mjs'
import { searchRemoteVideos } from './search/providers/index.mjs'
import { loadYouPornProfileAvatar } from './search/providers/youporn.mjs'
import { buildDesktopSiteLoginStatus, openDesktopSiteLoginWindow, clearDesktopSiteSession, buildCookieHeaderForUrl } from './site-login.mjs'
import { createSessionFetch, loadDocumentHtmlWithBrowserWindow } from './document-loader.mjs'
import { normalizeTargetUrl } from './cookie-header.mjs'
import { reloadRenderer, getDesktopWindowState } from './window.mjs'
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

export const installDesktopBridgeHandlers = () => {
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

    return resolveYouTubePlayback(normalizedUrl, {
      forceRefresh: options?.forceRefresh === true,
    })
  })

  ipcMain.removeHandler('desktop:resolve-youtube-subtitles')
  ipcMain.handle('desktop:resolve-youtube-subtitles', async (_event, targetUrl, options = {}) => {
    const normalizedUrl = normalizeTargetUrl(targetUrl)
    if (!normalizedUrl) {
      throw new Error('Invalid YouTube URL')
    }

    return resolveYouTubeSubtitles(normalizedUrl, {
      lang: String(options?.lang || '').trim(),
      format: String(options?.format || 'vtt').trim().toLowerCase(),
    })
  })

  ipcMain.removeHandler('desktop:resolve-bilibili-subtitles')
  ipcMain.handle('desktop:resolve-bilibili-subtitles', async (_event, targetUrl, options = {}) => {
    const normalizedUrl = normalizeTargetUrl(targetUrl)
    if (!normalizedUrl) {
      throw new Error('Invalid Bilibili URL')
    }

    const cookie = await buildCookieHeaderForUrl(normalizedUrl)
    return resolveBilibiliSubtitles(normalizedUrl, {
      cookie,
      lang: String(options?.lang || '').trim(),
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
      fetchImpl: createSessionFetch(),
    })
  })

  ipcMain.removeHandler('desktop:resolve-pornhub-playback')
  ipcMain.handle('desktop:resolve-pornhub-playback', async (_event, targetUrl, options = {}) => {
    const normalizedUrl = normalizeTargetUrl(targetUrl)
    if (!normalizedUrl) {
      throw new Error('Invalid Pornhub URL')
    }

    const cookie = await buildCookieHeaderForUrl(normalizedUrl)
    return resolvePornhubPlayback(normalizedUrl, {
      cookie,
      fetchImpl: createSessionFetch(),
      forceRefresh: options?.forceRefresh === true,
    })
  })

  ipcMain.removeHandler('desktop:resolve-javdb-playback')
  ipcMain.handle('desktop:resolve-javdb-playback', async (_event, targetUrl, options = {}) => {
    const normalizedUrl = normalizeTargetUrl(targetUrl)
    if (!normalizedUrl) {
      throw new Error('Invalid JavDB URL')
    }

    return resolveJavdbPlayback(normalizedUrl, {
      forceRefresh: options?.forceRefresh === true,
      title: options?.title,
      videoNo: options?.videoNo,
      loadDocumentHtml: loadDocumentHtmlWithBrowserWindow,
    })
  })

  ipcMain.removeHandler('desktop:resolve-javdb-metadata')
  ipcMain.handle('desktop:resolve-javdb-metadata', async (_event, targetUrl) => {
    const normalizedUrl = normalizeTargetUrl(targetUrl)
    if (!normalizedUrl) {
      throw new Error('Invalid JavDB URL')
    }

    return resolveJavdbMetadata(normalizedUrl, {
      loadDocumentHtml: loadDocumentHtmlWithBrowserWindow,
    })
  })

  ipcMain.removeHandler('desktop:resolve-youporn-playback')
  ipcMain.handle('desktop:resolve-youporn-playback', async (_event, targetUrl, options = {}) => {
    const normalizedUrl = normalizeTargetUrl(targetUrl)
    if (!normalizedUrl) {
      throw new Error('Invalid YouPorn URL')
    }

    const cookie = await buildCookieHeaderForUrl(normalizedUrl)
    return resolveYouPornPlayback(normalizedUrl, {
      cookie,
      fetchImpl: createSessionFetch(),
      forceRefresh: options?.forceRefresh === true,
    })
  })

  ipcMain.removeHandler('desktop:search-remote-videos')
  ipcMain.handle('desktop:search-remote-videos', async (_event, options = {}) => {
    return searchRemoteVideos({
      query: options?.query,
      site: options?.site || 'all',
      limit: options?.limit || 20,
      page: options?.page || 1,
      fetchImpl: createSessionFetch(),
      buildCookieHeader: buildCookieHeaderForUrl,
      loadDocumentHtml: loadDocumentHtmlWithBrowserWindow,
    })
  })

  ipcMain.removeHandler('desktop:get-remote-channel')
  ipcMain.handle('desktop:get-remote-channel', async (_event, options = {}) => {
    return getRemoteChannel({
      site: options?.site,
      url: options?.url,
      limit: options?.limit || 30,
      page: options?.page || 1,
      cursor: options?.cursor || null,
      profile: options?.profile || {},
      fetchImpl: createSessionFetch(),
      buildCookieHeader: buildCookieHeaderForUrl,
      loadDocumentHtml: loadDocumentHtmlWithBrowserWindow,
    })
  })

  ipcMain.removeHandler('desktop:get-youporn-profile-avatar')
  ipcMain.handle('desktop:get-youporn-profile-avatar', async (_event, profileUrl) => {
    return loadYouPornProfileAvatar({
      profileUrl,
      fetchImpl: createSessionFetch(),
      buildCookieHeader: buildCookieHeaderForUrl,
    })
  })

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
