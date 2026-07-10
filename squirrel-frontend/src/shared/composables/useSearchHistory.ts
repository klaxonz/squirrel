import { ref, type Ref } from 'vue'

/**
 * Recent-search history persisted to localStorage.
 *
 * Owns the recent-queries list (add/remove/clear + persistence), capped at a
 * max length with most-recent-first ordering and de-dup. Each search scope
 * owns an independent history so unrelated modules never suggest each
 * other's queries.
 *
 * Extracted from GlobalSearchBar.vue so the persistence round-trip + the
 * cap/dedup policy live in one reusable place rather than inline with the
 * suggestion-panel + desktop-playback wiring.
 */
const STORAGE_KEY_PREFIX = 'search-history'
const MAX_HISTORY = 10

export interface UseSearchHistoryReturn {
  recentSearches: Ref<string[]>
  addRecentSearch: (query: string) => void
  removeRecentSearch: (query: string) => void
  clearRecentSearches: () => void
}

const loadHistory = (storageKey: string): string[] => {
  try {
    const raw = localStorage.getItem(storageKey)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function useSearchHistory(scope: string): UseSearchHistoryReturn {
  const storageKey = `${STORAGE_KEY_PREFIX}:${scope}`
  const recentSearches = ref<string[]>(loadHistory(storageKey))

  const persist = () => {
    localStorage.setItem(storageKey, JSON.stringify(recentSearches.value))
  }

  const addRecentSearch = (query: string) => {
    const trimmed = query.trim()
    if (!trimmed) return
    // Most-recent-first, de-dup, cap at MAX_HISTORY.
    recentSearches.value = [trimmed, ...recentSearches.value.filter((s) => s !== trimmed)].slice(0, MAX_HISTORY)
    persist()
  }

  const removeRecentSearch = (query: string) => {
    recentSearches.value = recentSearches.value.filter((s) => s !== query)
    persist()
  }

  const clearRecentSearches = () => {
    recentSearches.value = []
    localStorage.removeItem(storageKey)
  }

  return {
    recentSearches,
    addRecentSearch,
    removeRecentSearch,
    clearRecentSearches,
  }
}
