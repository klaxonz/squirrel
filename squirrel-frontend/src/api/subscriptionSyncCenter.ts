import { get, post } from '@/utils/request'

export const getSyncCenterOverview = async <T = any>() => {
  return get<T>('/api/subscription/sync-center/overview')
}

export const getSyncCenterItems = async <T = any>(params: Record<string, unknown> = {}) => {
  return get<T>('/api/subscription/sync-center/items', params)
}

export const retryFailedSyncItems = async <T = any>(payload: Record<string, unknown> | null = null) => {
  return post<T>('/api/subscription/sync-center/retry-failed', payload)
}
