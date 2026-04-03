import { get } from '@/utils/request'

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

export const getSyncRuns = async <T = any>(params: Record<string, unknown> = {}) => {
  return get<T>('/api/subscription/sync-center/runs', buildNoCacheParams(params), noCacheConfig)
}

export const getSyncRunDetail = async <T = any>(runId: string) => {
  return get<T>(`/api/subscription/sync-center/runs/${encodeURIComponent(runId)}`, buildNoCacheParams(), noCacheConfig)
}

export const getSyncRunEvents = async <T = any>(runId: string) => {
  return get<T>(`/api/subscription/sync-center/runs/${encodeURIComponent(runId)}/events`, buildNoCacheParams(), noCacheConfig)
}
