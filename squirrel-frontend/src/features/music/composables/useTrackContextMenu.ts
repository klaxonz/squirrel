import { computed, onMounted, onUnmounted, reactive, type ComputedRef } from 'vue'
import type { MusicTrack } from '@/shared/api/music'
import type { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'

/**
 * Right-click context menu for a track list row.
 *
 * Owns the menu's open/close + position + target-track state, the absolute
 * position style, the document-level click-outside listener that closes it
 * (lifecycle-managed on mount/unmount), and the per-action handlers. Each
 * action closes the menu after firing. The play/insert-next actions drive the
 * player store; the navigation/playlist actions are injected so this composable
 * doesn't couple to the parent's emit surface.
 *
 * Extracted from MusicTrackList.vue so the click-outside lifecycle + the
 * "close after every action" contract live in one place.
 */
export interface TrackContextMenuState {
  visible: boolean
  x: number
  y: number
  track: MusicTrack | null
}

export interface UseTrackContextMenuOptions {
  player: ReturnType<typeof useMusicPlayerStore>
  onAddToPlaylist: (track: MusicTrack) => void
  onSelectArtist: (track: MusicTrack) => void
  onSelectAlbum: (track: MusicTrack) => void
}

export interface UseTrackContextMenuReturn {
  contextMenu: TrackContextMenuState
  contextMenuStyle: ComputedRef<{ left: string; top: string }>
  handleContextMenu: (track: MusicTrack, event: MouseEvent) => void
  closeContextMenu: () => void
  handleContextPlay: () => void
  handleContextInsertNext: () => void
  handleContextAddToPlaylist: () => void
  handleContextSelectArtist: () => void
  handleContextSelectAlbum: () => void
}

// Selector the click-outside guard looks for; the menu element carries this
// class so clicks inside it aren't treated as "outside".
const MENU_SELECTOR = '.music-context-menu'

export function useTrackContextMenu(options: UseTrackContextMenuOptions): UseTrackContextMenuReturn {
  const { player, onAddToPlaylist, onSelectArtist, onSelectAlbum } = options

  const contextMenu = reactive<TrackContextMenuState>({
    visible: false,
    x: 0,
    y: 0,
    track: null,
  })

  const contextMenuStyle = computed(() => ({
    left: `${contextMenu.x}px`,
    top: `${contextMenu.y}px`,
  }))

  const handleContextMenu = (track: MusicTrack, event: MouseEvent) => {
    contextMenu.visible = true
    contextMenu.x = event.clientX
    contextMenu.y = event.clientY
    contextMenu.track = track
  }

  const closeContextMenu = () => {
    contextMenu.visible = false
    contextMenu.track = null
  }

  const handleContextPlay = () => {
    if (contextMenu.track) player.playTrack(contextMenu.track)
    closeContextMenu()
  }

  const handleContextInsertNext = () => {
    if (contextMenu.track) player.insertNext(contextMenu.track)
    closeContextMenu()
  }

  const handleContextAddToPlaylist = () => {
    if (contextMenu.track) onAddToPlaylist(contextMenu.track)
    closeContextMenu()
  }

  const handleContextSelectArtist = () => {
    if (contextMenu.track && contextMenu.track.artist_id) onSelectArtist(contextMenu.track)
    closeContextMenu()
  }

  const handleContextSelectAlbum = () => {
    if (contextMenu.track && contextMenu.track.album_id) onSelectAlbum(contextMenu.track)
    closeContextMenu()
  }

  const handleClickOutside = (event: MouseEvent) => {
    if (!contextMenu.visible) return
    const target = event.target as HTMLElement
    if (!target.closest(MENU_SELECTOR)) closeContextMenu()
  }

  onMounted(() => {
    document.addEventListener('click', handleClickOutside)
  })

  onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside)
  })

  return {
    contextMenu,
    contextMenuStyle,
    handleContextMenu,
    closeContextMenu,
    handleContextPlay,
    handleContextInsertNext,
    handleContextAddToPlaylist,
    handleContextSelectArtist,
    handleContextSelectAlbum,
  }
}
