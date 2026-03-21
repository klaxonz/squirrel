import { get } from '@/utils/request'

export const getSyncTrends = async <T = any>(params: Record<string, unknown> = {}) => {
  return get<T>('/api/subscription/sync-center/trends', params)
}
