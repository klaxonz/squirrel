import { ipcMain } from 'electron'
import { resolveBilibiliPlayback, resolveBilibiliSubtitles } from './playback/providers/bilibili/index.mjs'
import { resolveYouTubePlayback, resolveYouTubeSubtitles } from './playback/providers/youtube/index.mjs'
import { createSessionFetch } from './document-loader.mjs'
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
}
