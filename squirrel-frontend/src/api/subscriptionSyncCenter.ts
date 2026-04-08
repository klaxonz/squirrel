import { get } from '@/utils/request'

export const getSyncCenterOverview = async <T = any>() => {
  return get<T>('/api/subscription/sync-center/overview')
}

export const getSyncCenterItems = async <T = any>(params: Record<string, unknown> = {}) => {
  return get<T>('/api/subscription/sync-center/items', params)
}

export const getFeedDashboardSnapshot = async <T = any>(params: Record<string, unknown> = {}) => {
  return get<T>('/api/subscription/sync-center/feed-snapshot', params)
}

export const getSyncCenterStreamUrl = (selectedRunId?: string | null) => {
  const params = new URLSearchParams()
  if (selectedRunId) {
    params.set('selectedRunId', selectedRunId)
  }
  const query = params.toString()
  return query ? `/api/subscription/sync-center/stream?${query}` : '/api/subscription/sync-center/stream'
}
