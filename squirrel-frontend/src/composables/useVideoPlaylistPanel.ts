import { computed, ref } from 'vue'
import type { Ref } from 'vue'

type VideoId = string | number

type VideoLike = {
  id?: VideoId
  [key: string]: unknown
}

type PlaylistLike = {
  id?: VideoId
  name?: string
  [key: string]: unknown
}

type PlaylistItemLike = {
  video_id?: VideoId
  video?: VideoLike | null
  [key: string]: unknown
}

type NavigateToVideo = (id: VideoId, videoData?: VideoLike | null) => Promise<void>
type SetAsideTab = (tab: 'related' | 'clips' | 'playlist') => void

export default function useVideoPlaylistPanel({
  video,
  playlists,
  activePlaylist,
  activePlaylistItems,
  fetchPlaylists,
  loadAndSetPlaylist,
  addVideo,
  createPlaylist,
  removeVideo,
  setCurrentVideo,
  goToVideo,
  setAsideTab,
}: {
  video: Ref<VideoLike | null>
  playlists: Ref<PlaylistLike[]>
  activePlaylist: Ref<PlaylistLike | null>
  activePlaylistItems: Ref<PlaylistItemLike[]>
  fetchPlaylists: () => Promise<unknown>
  loadAndSetPlaylist: (playlistId: VideoId) => Promise<unknown>
  addVideo: (videoId: VideoId, playlistId: VideoId) => Promise<PlaylistItemLike | null | undefined>
  createPlaylist: (name: string, description: string | null) => Promise<PlaylistLike | null | undefined>
  removeVideo: (playlistId: VideoId, videoId?: VideoId) => Promise<unknown>
  setCurrentVideo: (videoId: VideoId) => void
  goToVideo: NavigateToVideo
  setAsideTab: SetAsideTab
}) {
  const showPlaylistPicker = ref(false)
  const playlistPickerQuery = ref('')
  const newPlaylistName = ref('')
  const isPlaylistPickerSubmitting = ref(false)

  const filteredPlaylists = computed(() => {
    const query = playlistPickerQuery.value.trim().toLowerCase()
    if (!query) return playlists.value
    return playlists.value.filter((playlist) => String(playlist.name || '').toLowerCase().includes(query))
  })

  const currentVideoAlreadyInActivePlaylist = computed(() => {
    if (video.value?.id == null || !activePlaylist.value) return false
    return activePlaylistItems.value.some((item) => String(item.video_id) === String(video.value?.id))
  })

  const resetPlaylistPicker = () => {
    playlistPickerQuery.value = ''
    newPlaylistName.value = ''
    isPlaylistPickerSubmitting.value = false
  }

  const ensurePlaylistData = async () => {
    await fetchPlaylists()
    const nextPlaylistId = activePlaylist.value?.id ?? playlists.value[0]?.id
    if (nextPlaylistId != null) {
      await loadAndSetPlaylist(nextPlaylistId)
    }
  }

  const handlePlaylistPickerOpenChange = async (open: boolean) => {
    showPlaylistPicker.value = open
    if (!open) {
      resetPlaylistPicker()
      return
    }
    await fetchPlaylists()
  }

  const handleAddToPlaylist = async () => {
    if (video.value?.id == null) return
    showPlaylistPicker.value = true
    resetPlaylistPicker()
    await fetchPlaylists()
  }

  const selectActivePlaylist = async (playlistId: VideoId) => {
    setAsideTab('playlist')
    await loadAndSetPlaylist(playlistId)
  }

  const focusPlaylistTab = async (playlistId: VideoId | null = null) => {
    setAsideTab('playlist')
    await fetchPlaylists()
    const nextPlaylistId = playlistId ?? activePlaylist.value?.id ?? playlists.value[0]?.id
    if (nextPlaylistId != null) {
      await loadAndSetPlaylist(nextPlaylistId)
    }
  }

  const handleAddCurrentVideoToPlaylist = async (playlistId: VideoId) => {
    if (video.value?.id == null || isPlaylistPickerSubmitting.value) return

    isPlaylistPickerSubmitting.value = true
    try {
      const item = await addVideo(video.value.id, playlistId)
      if (!item) return

      await focusPlaylistTab(playlistId)
      showPlaylistPicker.value = false
    } finally {
      isPlaylistPickerSubmitting.value = false
    }
  }

  const handleCreatePlaylistFromPicker = async () => {
    const playlistName = newPlaylistName.value.trim()
    if (!playlistName || video.value?.id == null || isPlaylistPickerSubmitting.value) return

    isPlaylistPickerSubmitting.value = true
    try {
      const createdPlaylist = await createPlaylist(playlistName, null)
      if (!createdPlaylist?.id) return

      const item = await addVideo(video.value.id, createdPlaylist.id)
      if (!item) return

      await focusPlaylistTab(createdPlaylist.id)
      showPlaylistPicker.value = false
      newPlaylistName.value = ''
    } finally {
      isPlaylistPickerSubmitting.value = false
    }
  }

  const handleAddCurrentVideoToActivePlaylist = async () => {
    if (video.value?.id == null || !activePlaylist.value?.id || currentVideoAlreadyInActivePlaylist.value) return
    const item = await addVideo(video.value.id, activePlaylist.value.id)
    if (!item) return
    await loadAndSetPlaylist(activePlaylist.value.id)
  }

  const playPlaylistItem = async (item: PlaylistItemLike) => {
    if (item?.video?.id == null) return
    setCurrentVideo(item.video.id)
    await goToVideo(item.video.id, item.video)
  }

  const handleRemoveVideoFromActivePlaylist = async (item: PlaylistItemLike) => {
    if (!activePlaylist.value?.id) return
    await removeVideo(activePlaylist.value.id, item.video_id)
  }

  return {
    showPlaylistPicker,
    playlistPickerQuery,
    newPlaylistName,
    isPlaylistPickerSubmitting,
    filteredPlaylists,
    currentVideoAlreadyInActivePlaylist,
    ensurePlaylistData,
    handlePlaylistPickerOpenChange,
    handleAddToPlaylist,
    selectActivePlaylist,
    focusPlaylistTab,
    handleAddCurrentVideoToPlaylist,
    handleCreatePlaylistFromPicker,
    handleAddCurrentVideoToActivePlaylist,
    playPlaylistItem,
    handleRemoveVideoFromActivePlaylist,
  }
}
