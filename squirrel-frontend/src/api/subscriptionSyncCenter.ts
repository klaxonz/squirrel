import { get, post } from '@/utils/request'

const buildNoCacheParams = (params: Record<string, unknown> = {}) => ({
  ...params,
  _ts: Date.now(),
})

const noCacheConfig = {
  headers: {
    'Cache-Control': 'no-store',
    Pragma: 'no-cache',
  },
}

export const getSyncCenterOverview = async <T = any>() => {
  return get<T>('/api/subscription/sync-center/overview', buildNoCacheParams(), noCacheConfig)
}

export const getSyncCenterItems = async <T = any>(params: Record<string, unknown> = {}) => {
  return get<T>('/api/subscription/sync-center/items', buildNoCacheParams(params), noCacheConfig)
}

export const getFeedDashboardSnapshot = async <T = any>(params: Record<string, unknown> = {}) => {
  return get<T>('/api/subscription/sync-center/feed-snapshot', buildNoCacheParams(params), noCacheConfig)
}

export const retryFailedSyncItems = async <T = any>(payload: Record<string, unknown> | null = null) => {
  return post<T>('/api/subscription/sync-center/retry-failed', payload)
}
