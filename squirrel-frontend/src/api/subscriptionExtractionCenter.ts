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

export const getExtractionCenterOverview = async <T = any>() => {
  return get<T>('/api/subscription/extraction-center/overview', buildNoCacheParams(), noCacheConfig)
}

export const getExtractionCenterItems = async <T = any>(params: Record<string, unknown> = {}) => {
  return get<T>('/api/subscription/extraction-center/items', buildNoCacheParams(params), noCacheConfig)
}
