import { get } from '@/utils/request'

export const getVideoDetail = async (videoId: string | number) => {
  return get('/api/video/detail', { video_id: videoId })
}

export const getVideoList = async (params: Record<string, unknown> = {}) => {
  return get('/api/video/list', params)
}

export const getVideoSubtitles = async (
  videoId: string | number,
  { lang = 'ai-zh', fmt = 'srt' }: { lang?: string; fmt?: string } = {}
) => {
  return get(
    '/api/video/subtitles',
    { video_id: videoId, lang, fmt },
    { responseType: 'text' }
  )
}

export const getRandomVideo = async (params: Record<string, unknown> = {}) => {
  return get('/api/video/random', params)
}

export const getVideoCounts = async (params: Record<string, unknown> = {}) => {
  return get('/api/video/counts', params)
}

export const getVideoUrlInfo = async (
  videoId: string | number,
  {
    forceRefresh = false,
    clientType,
  }: {
    forceRefresh?: boolean
    clientType?: 'desktop'
  } = {}
) => {
  return get('/api/video/url', {
    video_id: videoId,
    ...(forceRefresh ? { force_refresh: true } : {}),
    ...(clientType ? { client_type: clientType } : {}),
  })
}
