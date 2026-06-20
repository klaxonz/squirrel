import { ref, watch, type ComputedRef, type Ref, type WatchSource } from 'vue'

/**
 * Music search history persisted to localStorage.
 *
 * Owns the recent-queries list (load/add/clear + persistence) and the watcher
 * that records a query as soon as it appears on the source. `addToHistory`
 * de-dupes and caps at MAX_HISTORY; the most recent entry is always first.
 *
 * Extracted from MusicSearchView.vue so the persistence round-trip + the
 * "record on query change" side effect live in one place rather than inline
 * with the view's presentation helpers.
 */
const HISTORY_KEY = 'squirrel_music_search_history'
const MAX_HISTORY = 15

export interface UseMusicSearchHistoryOptions {
  /** Source for the current search query; recorded when it becomes truthy. */
  query: WatchSource<string | undefined> | Ref<string | undefined> | ComputedRef<string | undefined>
}

export interface UseMusicSearchHistoryReturn {
  history: Ref<string[]>
  addToHistory: (query: string) => void
  clearHistory: () => void
}

const loadHistory = (): string[] => {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function useMusicSearchHistory(options: UseMusicSearchHistoryOptions): UseMusicSearchHistoryReturn {
  const { query } = options

  const history = ref<string[]>(loadHistory())

  const saveHistory = () => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.value))
  }

  const addToHistory = (q: string) => {
    const filtered = history.value.filter((k) => k !== q)
    history.value = [q, ...filtered].slice(0, MAX_HISTORY)
    saveHistory()
  }

  const clearHistory = () => {
    history.value = []
    saveHistory()
  }

  // Record a query as soon as it appears. The view used to set hasSearched
  // here too; that flag is now a local concern derived from query/result, so
  // this composable only owns the history side effect.
  watch(query, (val) => {
    if (val) addToHistory(val)
  }, { immediate: true })

  return {
    history,
    addToHistory,
    clearHistory,
  }
}
