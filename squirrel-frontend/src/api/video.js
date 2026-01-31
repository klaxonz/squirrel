import { get } from '@/utils/request'

export const getVideoDetail = async (videoId) => {
  return get('/api/video/detail', { video_id: videoId })
}

export const getVideoList = async (params = {}) => {
  return get('/api/video/list', params)
}

export const getVideoSubtitles = async (videoId, { lang = 'ai-zh', fmt = 'srt' } = {}) => {
  return get(
    '/api/video/subtitles',
    { video_id: videoId, lang, fmt },
    { responseType: 'text' }
  )
}

export const getRandomVideo = async (params = {}) => {
  return get('/api/video/random', params)
}

export const getVideoCounts = async (params = {}) => {
  return get('/api/video/counts', params)
}

export const getVideoUrlInfo = async (videoId, { forceRefresh = false } = {}) => {
  return get('/api/video/url', {
    video_id: videoId,
    ...(forceRefresh ? { force_refresh: true } : {}),
  })
}
