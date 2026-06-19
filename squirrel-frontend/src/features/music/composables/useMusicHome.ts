import { ref } from 'vue'
import {
  getMusicBanner,
  getMusicRanks,
  getMusicPlaylists,
  getMusicPlaylistTags,
  getMusicNewSongs,
  getMusicNewAlbums,
  getMusicHotSearch,
  getMusicAiRecommend,
  getMusicEverydayRecommend,
  type MusicPlaylist,
  type MusicRank,
  type MusicAlbum,
  type MusicHotSearch,
  type MusicPlaylistTag,
  type MusicTrack,
} from '@/shared/api/music'
import { Logger } from '@/shared/lib/logger'

export function useMusicHome() {
  const banners = ref<Array<{ id: string; title: string; cover: string }>>([])
  const bannerLoading = ref(false)
  const ranks = ref<MusicRank[]>([])
  const ranksLoading = ref(false)
  const playlists = ref<MusicPlaylist[]>([])
  const playlistsLoading = ref(false)
  const playlistTags = ref<MusicPlaylistTag[]>([])
  const selectedPlaylistCategory = ref(0)
  const playlistHasMore = ref(false)
  const newAlbums = ref<MusicAlbum[]>([])
  const newAlbumsLoading = ref(false)
  const newSongs = ref<MusicTrack[]>([])
  const newSongsLoading = ref(false)
  const hotSearches = ref<MusicHotSearch[]>([])
  const aiRecommend = ref<MusicTrack[]>([])
  const aiRecommendLoading = ref(false)
  const everydayRecommend = ref<MusicTrack[]>([])
  const everydayRecommendLoading = ref(false)

  async function loadHomeData() {
    await Promise.all([
      loadBanners(),
      loadRanks(),
      loadPlaylists(),
      loadNewAlbums(),
      loadHotSearches(),
    ])
  }

  async function loadBanners() {
    bannerLoading.value = true
    try {
      const { data, error } = await getMusicBanner()
      if (error) {
        Logger.warn('loadBanners failed', error)
        banners.value = []
        return
      }
      banners.value = data?.items || []
    } finally {
      bannerLoading.value = false
    }
  }

  async function loadRanks() {
    ranksLoading.value = true
    try {
      const { data, error } = await getMusicRanks()
      if (error) {
        Logger.warn('loadRanks failed', error)
        ranks.value = []
        return
      }
      ranks.value = data?.items || []
    } finally {
      ranksLoading.value = false
    }
  }

  async function loadPlaylists(_append = false) {
    playlistsLoading.value = true
    try {
      const { data, error } = await getMusicPlaylists({
        category_id: selectedPlaylistCategory.value,
        page: 1,
        page_size: 20,
      })
      if (error) {
        Logger.warn('loadPlaylists failed', error)
        playlists.value = []
        playlistHasMore.value = false
        return
      }
      playlists.value = data?.items || []
      playlistHasMore.value = data?.has_more || false
    } finally {
      playlistsLoading.value = false
    }
  }

  async function loadPlaylistTags() {
    try {
      const { data, error } = await getMusicPlaylistTags()
      if (error) {
        Logger.warn('loadPlaylistTags failed', error)
        playlistTags.value = []
        return
      }
      playlistTags.value = (data?.items || []).slice(0, 12) as MusicPlaylistTag[]
    } catch (err) {
      Logger.warn('loadPlaylistTags threw', err)
      playlistTags.value = []
    }
  }

  async function loadNewAlbums() {
    newAlbumsLoading.value = true
    try {
      const { data, error } = await getMusicNewAlbums({ page: 1, page_size: 30 })
      if (error) {
        Logger.warn('loadNewAlbums failed', error)
        newAlbums.value = []
        return
      }
      newAlbums.value = data?.items || []
    } finally {
      newAlbumsLoading.value = false
    }
  }

  async function loadNewAlbumsForView() {
    newAlbumsLoading.value = true
    try {
      const { data, error } = await getMusicNewAlbums({ page: 1, page_size: 30 })
      if (error) {
        Logger.warn('loadNewAlbumsForView failed', error)
        newAlbums.value = []
        return
      }
      newAlbums.value = data?.items || []
    } finally {
      newAlbumsLoading.value = false
    }
  }

  async function loadNewSongs() {
    newSongsLoading.value = true
    try {
      const { data, error } = await getMusicNewSongs({ page: 1, page_size: 50 })
      if (error) {
        Logger.warn('loadNewSongs failed', error)
        newSongs.value = []
        return
      }
      newSongs.value = data?.items || []
    } finally {
      newSongsLoading.value = false
    }
  }

  async function loadHotSearches() {
    try {
      const { data, error } = await getMusicHotSearch()
      if (error) {
        Logger.warn('loadHotSearches failed', error)
        hotSearches.value = []
        return
      }
      hotSearches.value = (data?.items || []).slice(0, 12) as MusicHotSearch[]
    } catch (err) {
      Logger.warn('loadHotSearches threw', err)
      hotSearches.value = []
    }
  }

  async function loadAiRecommend() {
    aiRecommendLoading.value = true
    try {
      const { data, error } = await getMusicAiRecommend({ page_size: 30 })
      if (error) {
        Logger.warn('loadAiRecommend failed', error)
        aiRecommend.value = []
        return
      }
      aiRecommend.value = data?.items || []
    } finally {
      aiRecommendLoading.value = false
    }
  }

  async function loadEverydayRecommend() {
    everydayRecommendLoading.value = true
    try {
      const { data, error } = await getMusicEverydayRecommend()
      if (error) {
        Logger.warn('loadEverydayRecommend failed', error)
        everydayRecommend.value = []
        return
      }
      everydayRecommend.value = data?.items || []
    } finally {
      everydayRecommendLoading.value = false
    }
  }

  async function handleSelectPlaylistCategory(categoryId: number) {
    selectedPlaylistCategory.value = categoryId
    await loadPlaylists()
  }

  async function handleLoadMorePlaylists() {
    if (playlistsLoading.value || !playlistHasMore.value) return
    playlistsLoading.value = true
    try {
      const { data, error } = await getMusicPlaylists({
        category_id: selectedPlaylistCategory.value,
        page: 2,
        page_size: 20,
      })
      if (error) {
        Logger.warn('handleLoadMorePlaylists failed', error)
        return
      }
      if (data?.items?.length) {
        playlists.value = [...playlists.value, ...data.items]
        playlistHasMore.value = data.has_more || false
      }
    } finally {
      playlistsLoading.value = false
    }
  }

  return {
    banners, bannerLoading,
    ranks, ranksLoading,
    playlists, playlistsLoading, playlistTags, selectedPlaylistCategory, playlistHasMore,
    newAlbums, newAlbumsLoading,
    newSongs, newSongsLoading,
    hotSearches,
    aiRecommend, aiRecommendLoading,
    everydayRecommend, everydayRecommendLoading,
    loadHomeData,
    loadNewAlbumsForView, loadNewSongs,
    loadPlaylistTags,
    loadAiRecommend, loadEverydayRecommend,
    handleSelectPlaylistCategory, handleLoadMorePlaylists,
  }
}
