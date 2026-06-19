import { get } from '@/shared/lib/request'

// Matches backend `serialize_rows` (domains/user/.../suggestions/formatting.py):
// every suggestion item is { type, value, label, meta } — all strings.
export type SearchSuggestionItem = {
  type: string
  value: string
  label: string
  meta: string
}

export type SearchSuggestionsResponse = {
  items: SearchSuggestionItem[]
  scope: string
  query: string | null
}

export const getSearchSuggestions = async (params: Record<string, unknown> = {}) => {
  return get<SearchSuggestionsResponse>('/api/search/suggestions', params)
}
