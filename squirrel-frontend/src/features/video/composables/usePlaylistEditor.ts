import { computed, ref, type ComputedRef, type Ref } from 'vue'
import type { Playlist } from '@/features/video/types/playlist'

/**
 * Create / edit-playlist form state machine.
 *
 * Owns the modal visibility (create vs edit), the two form fields, and the
 * save flow that dispatches to the injected `create`/`update` and closes the
 * modal. After a successful save it calls the injected `onSaved(playlist)` so
 * the host can re-sync its selection (e.g. switch to the just-created playlist)
 * without this composable reaching into selection internals.
 *
 * Extracted from PlaylistView.vue so the form-state + the create-vs-edit
 * branching live in one place rather than interleaved with selection + delete
 * orchestration.
 */
export interface UsePlaylistEditorOptions {
  /** Currently active playlist (used to pre-fill the edit form). */
  activePlaylist: ComputedRef<Playlist | null> | Ref<Playlist | null>
  /** Creates a playlist; returns it or null on failure. */
  create: (name: string, description?: string | null) => Promise<Playlist | null>
  /** Updates a playlist; returns it or null on failure. */
  update: (playlistId: Playlist['id'], name?: string | null, description?: string | null) => Promise<Playlist | null>
  /** Called after a successful create/update with the resulting playlist. */
  onSaved?: (playlist: Playlist) => void | Promise<void>
}

export interface UsePlaylistEditorReturn {
  showCreateModal: Ref<boolean>
  editingPlaylist: Ref<Playlist | null>
  formName: Ref<string>
  formDesc: Ref<string>
  editorOpen: ComputedRef<boolean>
  openCreateModal: () => void
  openEditModal: () => void
  closeModal: () => void
  handleEditorOpenChange: (open: boolean) => void
  handleSave: () => Promise<void>
}

export function usePlaylistEditor(options: UsePlaylistEditorOptions): UsePlaylistEditorReturn {
  const { activePlaylist, create, update, onSaved } = options

  const showCreateModal = ref(false)
  const editingPlaylist = ref<Playlist | null>(null)
  const formName = ref('')
  const formDesc = ref('')

  const editorOpen = computed(() => showCreateModal.value || !!editingPlaylist.value)

  const resetForm = () => {
    formName.value = ''
    formDesc.value = ''
  }

  const closeModal = () => {
    showCreateModal.value = false
    editingPlaylist.value = null
    resetForm()
  }

  const openCreateModal = () => {
    editingPlaylist.value = null
    resetForm()
    showCreateModal.value = true
  }

  const openEditModal = () => {
    const active = activePlaylist.value
    if (!active) return

    showCreateModal.value = false
    editingPlaylist.value = active
    formName.value = active.name
    formDesc.value = active.description || ''
  }

  const handleEditorOpenChange = (open: boolean) => {
    if (!open) closeModal()
  }

  const handleSave = async () => {
    const playlistName = formName.value.trim()
    const playlistDescription = formDesc.value.trim() || null
    if (!playlistName) return

    if (editingPlaylist.value) {
      const updated = await update(editingPlaylist.value.id, playlistName, playlistDescription)
      closeModal()
      if (updated) await onSaved?.(updated)
      return
    }

    const created = await create(playlistName, playlistDescription)
    closeModal()
    if (created) await onSaved?.(created)
  }

  return {
    showCreateModal,
    editingPlaylist,
    formName,
    formDesc,
    editorOpen,
    openCreateModal,
    openEditModal,
    closeModal,
    handleEditorOpenChange,
    handleSave,
  }
}
