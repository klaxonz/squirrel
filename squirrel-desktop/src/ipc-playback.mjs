import { ipcMain } from 'electron'
import { resolveBilibiliPlayback, resolveBilibiliSubtitles } from './playback/providers/bilibili/index.mjs'
import { resolveJavdbMetadata, resolveJavdbPlayback } from './playback/providers/javdb/index.mjs'
import { resolvePornhubPlayback } from './playback/providers/pornhub/index.mjs'
import { resolveYouPornPlayback } from './playback/providers/youporn/index.mjs'
import { resolveYouTubePlayback, resolveYouTubeSubtitles } from './playback/providers/youtube/index.mjs'
import { createSessionFetch, loadDocumentHtmlWithBrowserWindow } from './document-loader.mjs'
import { normalizeTargetUrl } from './cookie-header.mjs'
import { buildCookieHeaderForUrl } from './site-login.mjs'

export const installPlaybackHandlers = () => {
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
}
