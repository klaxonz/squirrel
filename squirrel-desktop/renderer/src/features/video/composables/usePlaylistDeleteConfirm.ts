import { ref, type ComputedRef, type Ref } from 'vue'
import type { Playlist } from '@/features/video/types/playlist'

/**
 * Delete-playlist confirm-dialog flow.
 *
 * Owns the confirm dialog visibility + the stashed delete target. `handleDelete`
 * stashes the target and opens the dialog; `confirmDelete` fires the injected
 * `remove` and, on success, calls `onDeleted(wasActive)` so the host can re-sync
 * its selection when the deleted playlist was the active one.
 *
 * Extracted from PlaylistView.vue so the stash→confirm→remove→re-sync flow
 * lives in one place rather than interleaved with editor + selection wiring.
 */
export interface UsePlaylistDeleteConfirmOptions {
  /** The current playlist list (used to resolve a delete target by id). */
  playlists: ComputedRef<Playlist[]> | Ref<Playlist[]>
  /** Whether a given playlist is the active one (drives post-delete re-sync). */
  isActive: (playlist: Playlist) => boolean
  /** Removes a playlist; returns true on success. */
  remove: (playlistId: Playlist['id']) => Promise<boolean>
  /** Called after a successful delete; receives whether the deleted one was active. */
  onDeleted?: (wasActive: boolean) => void | Promise<void>
}

export interface UsePlaylistDeleteConfirmReturn {
  showDeleteConfirm: Ref<boolean>
  deleteTargetPlaylist: Ref<Playlist | null>
  handleDelete: (playlistId: Playlist['id']) => void
  confirmDelete: () => Promise<void>
  closeDeleteConfirm: () => void
  handleDeleteConfirmOpenChange: (open: boolean) => void
}

export function usePlaylistDeleteConfirm(
  options: UsePlaylistDeleteConfirmOptions,
): UsePlaylistDeleteConfirmReturn {
  const { playlists, isActive, remove, onDeleted } = options

  const showDeleteConfirm = ref(false)
  const deleteTargetPlaylist = ref<Playlist | null>(null)

  const closeDeleteConfirm = () => {
    showDeleteConfirm.value = false
    deleteTargetPlaylist.value = null
  }

  const handleDeleteConfirmOpenChange = (open: boolean) => {
    if (!open) closeDeleteConfirm()
  }

  const handleDelete = (playlistId: Playlist['id']) => {
    const target = playlists.value.find((p) => String(p.id) === String(playlistId)) || null
    if (!target) return

    deleteTargetPlaylist.value = target
    showDeleteConfirm.value = true
  }

  const confirmDelete = async () => {
    const target = deleteTargetPlaylist.value
    if (!target) return

    const wasActive = isActive(target)
    const removed = await remove(target.id)

    closeDeleteConfirm()

    if (!removed) return
    await onDeleted?.(wasActive)
  }

  return {
    showDeleteConfirm,
    deleteTargetPlaylist,
    handleDelete,
    confirmDelete,
    closeDeleteConfirm,
    handleDeleteConfirmOpenChange,
  }
}
