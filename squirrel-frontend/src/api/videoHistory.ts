import { del, get, post } from '@/utils/request'

type VideoId = string | number

export const updateVideoHistory = async (payload: Record<string, unknown>) => {
  return post('/api/video-history/update', payload)
}

export const batchUpdateVideoHistory = async (reports: Record<string, unknown>[] = []) => {
  return post('/api/video-history/batch-update', { reports })
}

export const listVideoHistory = async (params: Record<string, unknown> = {}) => {
  return get('/api/video-history/list', params)
}

export const clearVideoHistory = async (videoIds: VideoId[] | null = null) => {
  const body = Array.isArray(videoIds) && videoIds.length ? videoIds : null
  return post('/api/video-history/clear', body)
}

export const deleteVideoHistory = async (historyId: VideoId) => {
  return del(`/api/video-history/${historyId}`)
}
