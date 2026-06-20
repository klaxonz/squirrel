import { computed, ref, type ComputedRef, type Ref } from 'vue'
import type { MusicTrack } from '@/shared/api/music'
import type { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'

/**
 * Multi-track selection state machine for a track list.
 *
 * Owns selection-mode + the selected-hash set, plus the toggle/select-all/exit
 * flows and the batch actions (play selected, add selected to playlist).
 * `handleRowClick` is the single entry that decides, per row, whether a click
 * toggles selection (when in selection mode) or plays the track.
 *
 * Selection is tracked by `hash` (the track's stable identity) rather than the
 * object reference, so it survives reactivity swaps of the tracks array.
 *
 * Extracted from MusicTrackList.vue so the selection state machine + the
 * "auto-exit selection mode when the set empties" policy live in one place.
 */
export interface UseTrackSelectionOptions {
  tracks: ComputedRef<MusicTrack[]> | Ref<MusicTrack[]>
  player: ReturnType<typeof useMusicPlayerStore>
  /** Emitted when the user adds the selected tracks to a playlist. */
  onAddToPlaylist: (tracks: MusicTrack[]) => void
}

export interface UseTrackSelectionReturn {
  selectionMode: Ref<boolean>
  selectedTracks: Ref<Set<string>>
  isAllSelected: ComputedRef<boolean>
  isPlaying: (track: MusicTrack) => boolean
  /** Row click handler. The MouseEvent is accepted (and ignored) so templates
   *  can bind `@click="handleRowClick(track, $event)"` without a wrapper. */
  handleRowClick: (track: MusicTrack, _event?: MouseEvent) => void
  toggleSelect: (track: MusicTrack) => void
  toggleSelectAll: () => void
  exitSelectionMode: () => void
  handlePlaySelected: () => void
  handleAddToPlaylist: () => void
}

export function useTrackSelection(options: UseTrackSelectionOptions): UseTrackSelectionReturn {
  const { tracks, player, onAddToPlaylist } = options

  const selectionMode = ref(false)
  const selectedTracks = ref<Set<string>>(new Set())

  const isAllSelected = computed(() => {
    if (tracks.value.length === 0) return false
    return tracks.value.every((t) => selectedTracks.value.has(t.hash))
  })

  const isPlaying = (track: MusicTrack): boolean => player.currentTrack?.hash === track.hash

  const exitSelectionMode = () => {
    selectedTracks.value.clear()
    selectionMode.value = false
  }

  const toggleSelect = (track: MusicTrack) => {
    if (selectedTracks.value.has(track.hash)) {
      selectedTracks.value.delete(track.hash)
      // Auto-exit selection mode once nothing remains selected — saves the user
      // a deliberate "cancel" click and matches the prior inline behaviour.
      if (selectedTracks.value.size === 0) {
        selectionMode.value = false
      }
    } else {
      selectedTracks.value.add(track.hash)
      selectionMode.value = true
    }
  }

  const toggleSelectAll = () => {
    if (isAllSelected.value) {
      selectedTracks.value.clear()
      selectionMode.value = false
    } else {
      tracks.value.forEach((t) => selectedTracks.value.add(t.hash))
      selectionMode.value = true
    }
  }

  // A row click's meaning depends on mode: toggle selection in selection mode,
  // play the track otherwise. The event arg is accepted for template ergonomics
  // (`@click="handleRowClick(track, $event)"`) and otherwise unused.
  const handleRowClick = (track: MusicTrack, _event?: MouseEvent) => {
    if (selectionMode.value) {
      toggleSelect(track)
    } else {
      player.playTrack(track)
    }
  }

  const handlePlaySelected = () => {
    const selected = tracks.value.filter((t) => selectedTracks.value.has(t.hash))
    if (selected.length > 0) {
      player.playQueue(selected, 0)
      exitSelectionMode()
    }
  }

  const handleAddToPlaylist = () => {
    const selected = tracks.value.filter((t) => selectedTracks.value.has(t.hash))
    if (selected.length > 0) {
      onAddToPlaylist(selected)
      exitSelectionMode()
    }
  }

  return {
    selectionMode,
    selectedTracks,
    isAllSelected,
    isPlaying,
    handleRowClick,
    toggleSelect,
    toggleSelectAll,
    exitSelectionMode,
    handlePlaySelected,
    handleAddToPlaylist,
  }
}
