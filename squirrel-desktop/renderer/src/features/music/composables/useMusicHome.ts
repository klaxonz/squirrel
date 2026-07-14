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

  // ponytail: each loader now uses the throw-based API — the old `{ data, error }`
  // + `if (error) { log; reset; return }` boilerplate collapses to a try/catch
  // where the catch resets the section to empty. Loaders stay silent on failure
  // (a failed section just renders empty; the view's empty state takes over).
  async function loadBanners() {
    bannerLoading.value = true
    try {
      const data = await getMusicBanner()
      banners.value = data?.items || []
    } catch (err) {
      Logger.warn('loadBanners failed', err)
      banners.value = []
    } finally {
      bannerLoading.value = false
    }
  }

  async function loadRanks() {
    ranksLoading.value = true
    try {
      const data = await getMusicRanks()
      ranks.value = data?.items || []
    } catch (err) {
      Logger.warn('loadRanks failed', err)
      ranks.value = []
    } finally {
      ranksLoading.value = false
    }
  }

  async function loadPlaylists(_append = false) {
    playlistsLoading.value = true
    try {
      const data = await getMusicPlaylists({
        category_id: selectedPlaylistCategory.value,
        page: 1,
        page_size: 20,
      })
      playlists.value = data?.items || []
      playlistHasMore.value = data?.has_more || false
    } catch (err) {
      Logger.warn('loadPlaylists failed', err)
      playlists.value = []
      playlistHasMore.value = false
    } finally {
      playlistsLoading.value = false
    }
  }

  async function loadPlaylistTags() {
    try {
      const data = await getMusicPlaylistTags()
      playlistTags.value = (data?.items || []).slice(0, 12) as MusicPlaylistTag[]
    } catch (err) {
      Logger.warn('loadPlaylistTags failed', err)
      playlistTags.value = []
    }
  }

  async function loadNewAlbums() {
    newAlbumsLoading.value = true
    try {
      const data = await getMusicNewAlbums({ page: 1, page_size: 30 })
      newAlbums.value = data?.items || []
    } catch (err) {
      Logger.warn('loadNewAlbums failed', err)
      newAlbums.value = []
    } finally {
      newAlbumsLoading.value = false
    }
  }

  async function loadNewAlbumsForView() {
    newAlbumsLoading.value = true
    try {
      const data = await getMusicNewAlbums({ page: 1, page_size: 30 })
      newAlbums.value = data?.items || []
    } catch (err) {
      Logger.warn('loadNewAlbumsForView failed', err)
      newAlbums.value = []
    } finally {
      newAlbumsLoading.value = false
    }
  }

  async function loadNewSongs() {
    newSongsLoading.value = true
    try {
      const data = await getMusicNewSongs({ page: 1, page_size: 50 })
      newSongs.value = data?.items || []
    } catch (err) {
      Logger.warn('loadNewSongs failed', err)
      newSongs.value = []
    } finally {
      newSongsLoading.value = false
    }
  }

  async function loadHotSearches() {
    try {
      const data = await getMusicHotSearch()
      hotSearches.value = (data?.items || []).slice(0, 12) as MusicHotSearch[]
    } catch (err) {
      Logger.warn('loadHotSearches failed', err)
      hotSearches.value = []
    }
  }

  async function loadAiRecommend() {
    aiRecommendLoading.value = true
    try {
      const data = await getMusicAiRecommend({ page_size: 30 })
      aiRecommend.value = data?.items || []
    } catch (err) {
      Logger.warn('loadAiRecommend failed', err)
      aiRecommend.value = []
    } finally {
      aiRecommendLoading.value = false
    }
  }

  async function loadEverydayRecommend() {
    everydayRecommendLoading.value = true
    try {
      const data = await getMusicEverydayRecommend()
      everydayRecommend.value = data?.items || []
    } catch (err) {
      Logger.warn('loadEverydayRecommend failed', err)
      everydayRecommend.value = []
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
      const data = await getMusicPlaylists({
        category_id: selectedPlaylistCategory.value,
        page: 2,
        page_size: 20,
      })
      if (data?.items?.length) {
        playlists.value = [...playlists.value, ...data.items]
        playlistHasMore.value = data.has_more || false
      }
    } catch (err) {
      Logger.warn('handleLoadMorePlaylists failed', err)
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
