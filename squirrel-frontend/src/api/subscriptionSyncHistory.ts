import { get } from '@/utils/request'

export const getSyncRuns = async <T = any>(params: Record<string, unknown> = {}) => {
  return get<T>('/api/subscription/sync-center/runs', params)
}

export const getSyncRunDetail = async <T = any>(runId: string) => {
  return get<T>(`/api/subscription/sync-center/runs/${encodeURIComponent(runId)}`)
}

export const getSyncRunEvents = async <T = any>(runId: string) => {
  return get<T>(`/api/subscription/sync-center/runs/${encodeURIComponent(runId)}/events`)
}
