import { get } from '@/utils/request'

export const getSearchSuggestions = async (params: Record<string, unknown> = {}) => {
  return get('/api/search/suggestions', params)
}
