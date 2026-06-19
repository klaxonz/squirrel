import { ref, computed } from 'vue'
import {
  listPlaylists,
  getPlaylistDetail,
  getPlaylistItems,
  createPlaylist,
  updatePlaylist,
  deletePlaylist,
  addVideoToPlaylist,
  removeVideoFromPlaylist,
  reorderPlaylistItem,
  getDefaultPlaylist,
} from '@/shared/api/playlist'
import type { Playlist, PlaylistDetail, PlaylistItem, VideoBasic, PlaylistId, VideoId } from '@/features/video/types/playlist'
import { Logger } from '@/shared/lib/logger'

const createPlaylistStore = () => {
  const playlists = ref<Playlist[]>([])
  const activePlaylist = ref<PlaylistDetail | null>(null)
  const activePlaylistItems = ref<PlaylistItem[]>([])
  const loading = ref(false)
  const loadingItems = ref(false)
  const error = ref<string | null>(null)

  const currentIndex = ref(-1)
  const currentVideoId = ref<VideoId | null>(null)

  const currentVideo = computed(() => {
    if (currentIndex.value < 0 || !activePlaylistItems.value.length) {
      return null
    }
    return activePlaylistItems.value[currentIndex.value] || null
  })

  const hasPrev = computed(() => {
    if (currentIndex.value <= 0) return false
    return true
  })

  const hasNext = computed(() => {
    if (currentIndex.value < 0) return false
    if (activePlaylistItems.value.length === 0) return false
    return currentIndex.value < activePlaylistItems.value.length - 1
  })

  const setCurrentVideo = (videoId: VideoId | null) => {
    currentVideoId.value = videoId
    if (videoId === null) {
      currentIndex.value = -1
      return
    }
    const idx = activePlaylistItems.value.findIndex(
      item => String(item.video_id) === String(videoId)
    )
    currentIndex.value = idx
  }

  const fetchPlaylists = async () => {
    loading.value = true
    error.value = null
    try {
      const data = await listPlaylists()
      playlists.value = data || []
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载失败'
      Logger.error('[usePlaylist] fetchPlaylists error', err)
    } finally {
      loading.value = false
    }
  }

  const fetchPlaylistDetail = async (playlistId: PlaylistId) => {
    loading.value = true
    error.value = null
    try {
      const data = await getPlaylistDetail(playlistId)
      activePlaylist.value = data || null
      return data || null
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载失败'
      Logger.error('[usePlaylist] fetchPlaylistDetail error', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const fetchPlaylistItems = async (playlistId: PlaylistId) => {
    loadingItems.value = true
    try {
      const data = await getPlaylistItems(playlistId)
      activePlaylistItems.value = data || []
      setCurrentVideo(currentVideoId.value)
      return data || []
    } catch (err) {
      Logger.error('[usePlaylist] fetchPlaylistItems error', err)
      return []
    } finally {
      loadingItems.value = false
    }
  }

  const loadAndSetPlaylist = async (playlistId: PlaylistId) => {
    await fetchPlaylistDetail(playlistId)
    const items = await fetchPlaylistItems(playlistId)
    return items
  }

  const create = async (name: string, description?: string | null) => {
    try {
      const data = await createPlaylist({ name, description })
      if (data) {
        playlists.value.unshift(data)
      }
      return data
    } catch (err) {
      Logger.error('[usePlaylist] create error', err)
      return null
    }
  }

  const update = async (playlistId: PlaylistId, name?: string | null, description?: string | null) => {
    try {
      const data = await updatePlaylist(playlistId, { name, description })
      if (data) {
        const idx = playlists.value.findIndex(p => String(p.id) === String(playlistId))
        if (idx !== -1) {
          playlists.value[idx] = { ...playlists.value[idx], ...data }
        }
        if (activePlaylist.value && String(activePlaylist.value.id) === String(playlistId)) {
          activePlaylist.value = { ...activePlaylist.value, ...data }
        }
      }
      return data
    } catch (err) {
      Logger.error('[usePlaylist] update error', err)
      return null
    }
  }

  const remove = async (playlistId: PlaylistId) => {
    try {
      await deletePlaylist(playlistId)
    } catch (err) {
      Logger.error('[usePlaylist] delete error', err)
      return false
    }
    playlists.value = playlists.value.filter(p => String(p.id) !== String(playlistId))
    if (activePlaylist.value && String(activePlaylist.value.id) === String(playlistId)) {
      activePlaylist.value = null
      activePlaylistItems.value = []
    }
    return true
  }

  const addVideo = async (videoId: VideoId, playlistId?: PlaylistId | null) => {
    try {
      const data = await addVideoToPlaylist({
        video_id: videoId,
        playlist_id: playlistId,
      })
      if (data) {
        const resolvedPlaylistId = playlistId ?? data.playlist_id
        if (resolvedPlaylistId !== null && resolvedPlaylistId !== undefined) {
          if (activePlaylist.value && String(activePlaylist.value.id) === String(resolvedPlaylistId)) {
            await fetchPlaylistDetail(resolvedPlaylistId)
            await fetchPlaylistItems(resolvedPlaylistId)
          }
          await fetchPlaylists()
        }
      }
      return data
    } catch (err) {
      Logger.error('[usePlaylist] addVideo error', err)
      return null
    }
  }

  const removeVideo = async (playlistId: PlaylistId, videoId: VideoId) => {
    try {
      await removeVideoFromPlaylist(playlistId, videoId)
    } catch (err) {
      Logger.error('[usePlaylist] removeVideo error', err)
      return false
    }
    const idx = activePlaylistItems.value.findIndex(
      item => String(item.video_id) === String(videoId)
    )
    if (idx !== -1) {
      activePlaylistItems.value.splice(idx, 1)
    }
    const p = playlists.value.find(p => String(p.id) === String(playlistId))
    if (p && p.video_count > 0) {
      p.video_count -= 1
    }
    if (currentIndex.value >= activePlaylistItems.value.length) {
      currentIndex.value = Math.max(-1, activePlaylistItems.value.length - 1)
    }
    return true
  }

  const reorder = async (playlistId: PlaylistId, videoId: VideoId, newPosition: number) => {
    try {
      const data = await reorderPlaylistItem({
        playlist_id: playlistId,
        video_id: videoId,
        new_position: newPosition,
      })
      if (data && activePlaylist.value && String(activePlaylist.value.id) === String(playlistId)) {
        await fetchPlaylistItems(playlistId)
      }
      return true
    } catch (err) {
      Logger.error('[usePlaylist] reorder error', err)
      return false
    }
  }

  const goToPrev = (): VideoBasic | null => {
    if (!hasPrev.value) return null
    currentIndex.value -= 1
    const item = activePlaylistItems.value[currentIndex.value]
    if (item?.video) {
      currentVideoId.value = item.video.id
      return item.video
    }
    return null
  }

  const goToNext = (): VideoBasic | null => {
    if (!hasNext.value) return null
    currentIndex.value += 1
    const item = activePlaylistItems.value[currentIndex.value]
    if (item?.video) {
      currentVideoId.value = item.video.id
      return item.video
    }
    return null
  }

  const getDefault = async (): Promise<Playlist | null> => {
    try {
      const data = await getDefaultPlaylist()
      return data || null
    } catch (err) {
      Logger.error('[usePlaylist] getDefault error', err)
      return null
    }
  }

  const playItem = (item: PlaylistItem): VideoBasic | null => {
    if (item?.video) {
      setCurrentVideo(item.video.id)
      return item.video
    }
    return null
  }

  return {
    playlists,
    activePlaylist,
    activePlaylistItems,
    loading,
    loadingItems,
    error,
    currentIndex,
    currentVideoId,
    currentVideo,
    hasPrev,
    hasNext,

    fetchPlaylists,
    fetchPlaylistDetail,
    fetchPlaylistItems,
    loadAndSetPlaylist,
    create,
    update,
    remove,
    addVideo,
    removeVideo,
    reorder,
    setCurrentVideo,
    goToPrev,
    goToNext,
    getDefault,
    playItem,
  }
}

const playlistStore = createPlaylistStore()

export function usePlaylist() {
  return playlistStore
}
