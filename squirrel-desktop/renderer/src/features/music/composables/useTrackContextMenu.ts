import { computed, reactive, type ComputedRef } from 'vue'
import type { MusicTrack } from '@/shared/api/music'
import type { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'

/**
 * Owns track-target state and menu actions. Shared AppContextMenu owns menu
 * chrome, outside-click handling, and Escape behavior so feature components do
 * not each implement their own popup contract.
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
  contextMenuPosition: ComputedRef<{ x: number; y: number }>
  handleContextMenu: (track: MusicTrack, event: MouseEvent) => void
  closeContextMenu: () => void
  handleContextPlay: () => void
  handleContextInsertNext: () => void
  handleContextAddToPlaylist: () => void
  handleContextSelectArtist: () => void
  handleContextSelectAlbum: () => void
}

export function useTrackContextMenu(options: UseTrackContextMenuOptions): UseTrackContextMenuReturn {
  const { player, onAddToPlaylist, onSelectArtist, onSelectAlbum } = options

  const contextMenu = reactive<TrackContextMenuState>({
    visible: false,
    x: 0,
    y: 0,
    track: null,
  })

  const contextMenuPosition = computed(() => ({
    x: contextMenu.x,
    y: contextMenu.y,
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

  return {
    contextMenu,
    contextMenuPosition,
    handleContextMenu,
    closeContextMenu,
    handleContextPlay,
    handleContextInsertNext,
    handleContextAddToPlaylist,
    handleContextSelectArtist,
    handleContextSelectAlbum,
  }
}
