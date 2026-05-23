import type { AxiosRequestConfig } from 'axios'
import { get, post } from '@/utils/request'

export const getVideoDetail = async (videoId: string | number) => {
  return get('/api/video/detail', { video_id: videoId })
}

export const getVideoList = async (params: Record<string, unknown> = {}, config: AxiosRequestConfig = {}) => {
  return get('/api/video/list', params, config)
}

export const getVideoSubtitles = async (
  videoId: string | number,
  { lang, fmt = 'srt' }: { lang?: string; fmt?: string } = {}
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

export const saveRemoteVideo = async (data: Record<string, unknown>) => {
  return post('/api/video/remote/save', data)
}
