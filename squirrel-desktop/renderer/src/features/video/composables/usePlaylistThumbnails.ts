import { ref, type ComputedRef, type Ref } from 'vue'
import type { Playlist, PlaylistItem } from '@/features/video/types/playlist'

/**
 * Cached 4-up thumbnail projection for a playlist.
 *
 * Returns the first 4 video thumbnails for a playlist's items, memoised in a
 * per-id Map so repeated reads don't re-slice the items array. Only the active
 * playlist's items are loaded in-memory (other playlists' thumbnails aren't
 * fetched until opened), so this returns [] for non-active playlists — the
 * caller renders a placeholder for those.
 *
 * Extracted from PlaylistView.vue so the cache + the "only the active playlist
 * has items" invariant live in one reusable place.
 */
export interface UsePlaylistThumbnailsOptions {
  activePlaylist: ComputedRef<Playlist | null> | Ref<Playlist | null>
  activePlaylistItems: ComputedRef<PlaylistItem[]> | Ref<PlaylistItem[]>
}

export interface UsePlaylistThumbnailsReturn {
  getPlaylistThumbnails: (playlist: Playlist) => string[]
}

export function usePlaylistThumbnails(options: UsePlaylistThumbnailsOptions): UsePlaylistThumbnailsReturn {
  const { activePlaylist, activePlaylistItems } = options

  const cache = ref<Map<string | number, string[]>>(new Map())

  const getPlaylistThumbnails = (playlist: Playlist): string[] => {
    const cached = cache.value.get(playlist.id)
    if (cached) return cached

    // Only the active playlist has its items loaded in memory; other playlists
    // haven't been fetched, so there are no thumbnails to project yet.
    const items =
      activePlaylist.value && String(activePlaylist.value.id) === String(playlist.id)
        ? activePlaylistItems.value
        : []

    const thumbs = items
      .map((item) => item.video?.thumbnail)
      .filter((thumbnail): thumbnail is string => !!thumbnail)
      .slice(0, 4)

    if (thumbs.length > 0) {
      cache.value.set(playlist.id, thumbs)
    }
    return thumbs
  }

  return { getPlaylistThumbnails }
}
