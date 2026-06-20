import { ref, type Ref } from 'vue'

/**
 * Recent-search history persisted to localStorage.
 *
 * Owns the recent-queries list (add/remove/clear + persistence), capped at a
 * max length with most-recent-first ordering and de-dup. Mirrors the
 * useMusicSearchHistory pattern but for the generic global search bar, whose
 * history lives under a different storage key ('search-history').
 *
 * Extracted from GlobalSearchBar.vue so the persistence round-trip + the
 * cap/dedup policy live in one reusable place rather than inline with the
 * suggestion-panel + desktop-playback wiring.
 */
const STORAGE_KEY = 'search-history'
const MAX_HISTORY = 10

export interface UseSearchHistoryReturn {
  recentSearches: Ref<string[]>
  addRecentSearch: (query: string) => void
  removeRecentSearch: (query: string) => void
  clearRecentSearches: () => void
}

const loadHistory = (): string[] => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function useSearchHistory(): UseSearchHistoryReturn {
  const recentSearches = ref<string[]>(loadHistory())

  const persist = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(recentSearches.value))
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
    localStorage.removeItem(STORAGE_KEY)
  }

  return {
    recentSearches,
    addRecentSearch,
    removeRecentSearch,
    clearRecentSearches,
  }
}
