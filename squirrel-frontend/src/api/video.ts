import type { AxiosRequestConfig } from 'axios'
import { get, post } from '@/utils/request'
import type { VideoListResponse, VideoDetail, RandomVideoResult } from '@/types/video'
import type { VideoPageVideo } from '@/types/videoPlayback'

type YesNoAll = 'all' | 'yes' | 'no'
type TimeRange = 'all' | 'today' | 'week' | 'month' | 'year'
type DurationFilter = 'all' | 'short' | 'medium' | 'long'
type ContentType = 'all' | 'CHANNEL' | 'PLAYLIST' | 'ACTRESS' | 'MOVIE' | 'TV_SERIES' | 'ACTOR'
type Category = 'all' | 'read' | 'unread' | 'preview' | 'liked' | 'later'
type SortBy = 'publish_date' | 'created_at'

export type VideoListParams = {
  query?: string
  subscription_id?: number | string | null
  // ponytail: backend accepts arbitrary category/sort strings beyond the known
  // enum; typed as the union plus a bare string escape hatch for forward-compat.
  category?: Category | (string & {})
  sort_by?: SortBy | (string & {})
  nsfw?: YesNoAll | string
  special?: YesNoAll | string
  site?: string
  cursor?: string | null
  pageSize?: number | string
  page_size?: number | string
  time_range?: TimeRange | string
  duration?: DurationFilter | string
  content_type?: ContentType | string
}

export type RandomVideoParams = {
  category?: Category | (string & {})
  subscription_id?: number
  nsfw?: YesNoAll
  site?: string
  query?: string
  time_range?: TimeRange | string
  duration?: DurationFilter | string
  content_type?: ContentType | string
}

export const getVideoDetail = async (videoId: string | number) => {
  return get<VideoDetail>('/api/video/detail', { video_id: videoId })
}

export const getVideoList = async (params: VideoListParams = {}, config: AxiosRequestConfig = {}) => {
  return get<VideoListResponse>('/api/video/list', params, config)
}

export const getVideoSubtitles = async (
  videoId: string | number,
  { lang, fmt = 'srt' }: { lang?: string; fmt?: string } = {}
) => {
  return get<string>(
    '/api/video/subtitles',
    { video_id: videoId, lang, fmt },
    { responseType: 'text' }
  )
}

export const getRandomVideo = async (params: RandomVideoParams = {}) => {
  return get<RandomVideoResult>('/api/video/random', params)
}

export const saveRemoteVideo = async (data: Record<string, unknown>) => {
  return post<VideoPageVideo>('/api/video/remote-save', data)
}
