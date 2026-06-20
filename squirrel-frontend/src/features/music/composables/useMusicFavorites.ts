import { computed, ref, type ComputedRef, type Ref } from 'vue'
import { addMusicFavorite, removeMusicFavorite } from '@/shared/api/music'
import type { MusicTrack } from '@/shared/api/music'

/**
 * Track-favorite (like) state machine.
 *
 * Owns the per-`album_audio_id` liked set, the toggle-with-optimistic-update +
 * loading guard, and the `isTrackLiked` projection for the heart icon. The
 * liked set is keyed by `album_audio_id` (the favorite API's stable identity).
 *
 * A failed add/remove is silent and leaves the heart unchanged — the user can
 * retry, and we never show a like the backend rejected.
 *
 * Extracted from GlobalMusicPlayerBar.vue so the optimistic-update + guard
 * policy lives in one reusable place; any track surface that renders a heart
 * can consume it.
 */
export interface UseMusicFavoritesOptions {
  currentTrack: ComputedRef<MusicTrack | null | undefined> | Ref<MusicTrack | null | undefined>
}

export interface UseMusicFavoritesReturn {
  likedTracks: Ref<Set<string>>
  likeLoading: Ref<boolean>
  isTrackLiked: ComputedRef<boolean>
  toggleLike: () => Promise<void>
}

export function useMusicFavorites(options: UseMusicFavoritesOptions): UseMusicFavoritesReturn {
  const { currentTrack } = options

  const likedTracks = ref<Set<string>>(new Set())
  const likeLoading = ref(false)

  const isTrackLiked = computed(() => {
    const track = currentTrack.value
    if (!track?.album_audio_id) return false
    return likedTracks.value.has(track.album_audio_id)
  })

  const toggleLike = async () => {
    const track = currentTrack.value
    if (!track?.album_audio_id || likeLoading.value) return

    likeLoading.value = true
    try {
      if (isTrackLiked.value) {
        await removeMusicFavorite(track.album_audio_id)
        likedTracks.value.delete(track.album_audio_id)
      } else {
        await addMusicFavorite(track.album_audio_id)
        likedTracks.value.add(track.album_audio_id)
      }
    } catch {
      // silent — a failed like toggle leaves the heart state unchanged so the
      // user can retry; we never show a like the backend rejected.
    } finally {
      likeLoading.value = false
    }
  }

  return {
    likedTracks,
    likeLoading,
    isTrackLiked,
    toggleLike,
  }
}
