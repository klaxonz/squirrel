import type { AxiosRequestConfig } from 'axios'
import { get, post } from '@/utils/request'

type YesNoAll = 'all' | 'yes' | 'no'
type TimeRange = 'all' | 'today' | 'week' | 'month' | 'year'
type DurationFilter = 'all' | 'short' | 'medium' | 'long'
type ContentType = 'all' | 'CHANNEL' | 'PLAYLIST' | 'ACTRESS' | 'MOVIE' | 'TV_SERIES' | 'ACTOR'

export type VideoListParams = {
  query?: string
  subscription_id?: number | string | null
  category?: 'all' | 'read' | 'unread' | 'preview' | 'liked' | 'later' | (string & {})
  sort_by?: 'publish_date' | 'created_at' | (string & {})
  nsfw?: YesNoAll | string
  special?: YesNoAll | (string & {})
  site?: string
  withTotal?: boolean
  page?: number
  pageSize?: number | string
  page_size?: number | string
  time_range?: TimeRange | (string & {})
  duration?: DurationFilter | (string & {})
  content_type?: ContentType | (string & {})
}

export type RandomVideoParams = {
  category?: 'all' | 'read' | 'unread' | 'preview' | 'liked' | 'later' | (string & {})
  subscription_id?: number
  nsfw?: YesNoAll
  site?: string
  query?: string
  time_range?: TimeRange | (string & {})
  duration?: DurationFilter | (string & {})
  content_type?: ContentType | (string & {})
}

export const getVideoDetail = async (videoId: string | number) => {
  return get('/api/video/detail', { video_id: videoId })
}

export const getVideoList = async (params: VideoListParams = {}, config: AxiosRequestConfig = {}) => {
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

export const getRandomVideo = async (params: RandomVideoParams = {}) => {
  return get('/api/video/random', params)
}

export const saveRemoteVideo = async (data: Record<string, unknown>) => {
  return post('/api/video/remote-save', data)
}
