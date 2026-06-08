import { ipcMain } from 'electron'
import { getRemoteChannel } from './search/providers/remote-channel.mjs'
import { searchRemoteVideos } from './search/providers/index.mjs'
import { loadYouPornProfileAvatar } from './search/providers/youporn.mjs'
import { createSessionFetch, loadDocumentHtmlWithBrowserWindow } from './document-loader.mjs'
import { buildCookieHeaderForUrl } from './site-login.mjs'

export const installSearchHandlers = () => {
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
}
