import { ref, type Ref } from 'vue'
import { searchMusicComplex, type MusicAlbum, type MusicArtist, type MusicTrack } from '@/shared/api/music'
import { Logger } from '@/shared/lib/logger'

/**
 * Music complex-search state + execution.
 *
 * Owns the query/loading/error/result quartet for the complex (songs + artists
 * + albums) search, plus the execute + reset flows. `handleSearch` normalises
 * the query and surfaces backend errors as a user-facing string; `resetSearch`
 * clears state and, when the user is currently on the search view, hands off to
 * the injected `onResetWhenSearching` callback so the view can navigate home
 * without this composable reaching into navigation internals.
 *
 * Extracted from Music.vue so the error-string mapping + the empty-query reset
 * policy live in one place.
 */
export interface MusicComplexResult {
  songs: MusicTrack[]
  artists: MusicArtist[]
  albums: MusicAlbum[]
}

export interface UseMusicSearchOptions {
  /** Invoked by resetSearch when the user is currently on the search view. */
  onResetWhenSearching: () => void
  /** Returns whether the active view is the search view. */
  isSearchView: () => boolean
}

export interface UseMusicSearchReturn {
  searchLoading: Ref<boolean>
  searchError: Ref<string | null>
  complexResult: Ref<MusicComplexResult | null>
  searchQuery: Ref<string>
  handleSearch: (query: string) => Promise<void>
  resetSearch: () => void
}

export function useMusicSearch(options: UseMusicSearchOptions): UseMusicSearchReturn {
  const { onResetWhenSearching, isSearchView } = options

  const searchLoading = ref(false)
  const searchError = ref<string | null>(null)
  const complexResult = ref<MusicComplexResult | null>(null)
  const searchQuery = ref('')

  const handleSearch = async (query: string) => {
    const normalizedQuery = query.trim()
    if (!normalizedQuery) {
      resetSearch()
      return
    }
    searchQuery.value = normalizedQuery
    searchLoading.value = true
    searchError.value = null
    try {
      const data = await searchMusicComplex(normalizedQuery)
      complexResult.value = data || { songs: [], artists: [], albums: [] }
    } catch (err) {
      Logger.warn('handleSearch failed', err)
      searchError.value = err instanceof Error ? err.message : '搜索失败，请稍后重试'
      complexResult.value = null
    } finally {
      searchLoading.value = false
    }
  }

  const resetSearch = () => {
    searchQuery.value = ''
    searchLoading.value = false
    complexResult.value = null
    if (isSearchView()) {
      onResetWhenSearching()
    }
  }

  return {
    searchLoading,
    searchError,
    complexResult,
    searchQuery,
    handleSearch,
    resetSearch,
  }
}
