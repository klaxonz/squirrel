import { get } from '@/utils/request'

export const getExtractionCenterOverview = async <T = any>() => {
  return get<T>('/api/subscription/extraction-center/overview')
}

export const getExtractionCenterItems = async <T = any>(params: Record<string, unknown> = {}) => {
  return get<T>('/api/subscription/extraction-center/items', params)
}
