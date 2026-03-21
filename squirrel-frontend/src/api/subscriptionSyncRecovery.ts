import { get, post } from '@/utils/request'

export const getSyncRecoverySummary = async <T = any>() => {
  return get<T>('/api/subscription/sync-center/recovery-summary')
}

export const reconcileSyncCenter = async <T = any>() => {
  return post<T>('/api/subscription/sync-center/reconcile', null)
}
