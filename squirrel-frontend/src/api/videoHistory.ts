import { del, get, post } from '@/utils/request'
import type { VideoHistoryListResponse } from '@/types/video'

type VideoId = string | number

export interface VideoHistoryReport {
  video_id: number
  last_position?: number
  timestamp?: number | null
}

export const updateVideoHistory = async (payload: VideoHistoryReport) => {
  return post('/api/video-history/update', payload)
}

export const batchUpdateVideoHistory = async (reports: VideoHistoryReport[] = []) => {
  return post('/api/video-history/batch-update', { reports })
}

export const listVideoHistory = async (params: Record<string, unknown> = {}) => {
  return get<VideoHistoryListResponse>('/api/video-history/list', params)
}

export const clearVideoHistory = async (videoIds: VideoId[] | null = null) => {
  const body = Array.isArray(videoIds) && videoIds.length ? videoIds : null
  return post('/api/video-history/clear', body)
}

export const deleteVideoHistory = async (historyId: VideoId) => {
  return del(`/api/video-history/${historyId}`)
}
