import { get } from '@/utils/request'

export const getSearchSuggestions = async (params: Record<string, unknown> = {}) => {
  return get<{ items?: unknown[] }>('/api/search/suggestions', params)
}
