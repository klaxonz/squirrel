import { get, post } from '@/utils/request'

export const updateVideoHistory = async (payload) => {
  return post('/api/video-history/update', payload)
}

export const batchUpdateVideoHistory = async (reports = []) => {
  return post('/api/video-history/batch-update', { reports })
}

export const listVideoHistory = async (params = {}) => {
  return get('/api/video-history/list', params)
}

export const clearVideoHistory = async (videoIds = null) => {
  const body = Array.isArray(videoIds) && videoIds.length ? videoIds : null
  return post('/api/video-history/clear', body)
}
