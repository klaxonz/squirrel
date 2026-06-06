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
} from '@/api/music'
import { Logger } from '@/utils/logger'

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
    const { data } = await getMusicBanner()
    bannerLoading.value = false
    banners.value = data?.items || []
  }

  async function loadRanks() {
    ranksLoading.value = true
    const { data } = await getMusicRanks()
    ranksLoading.value = false
    ranks.value = data?.items || []
  }

  async function loadPlaylists(append = false) {
    playlistsLoading.value = true
    const { data } = await getMusicPlaylists({
      category_id: selectedPlaylistCategory.value,
      page: 1,
      page_size: 20,
    })
    playlistsLoading.value = false
    playlists.value = data?.items || []
    playlistHasMore.value = data?.has_more || false
  }

  async function loadPlaylistTags() {
    const { data } = await getMusicPlaylistTags()
    playlistTags.value = (data?.items || []).slice(0, 12) as MusicPlaylistTag[]
  }

  async function loadNewAlbums() {
    newAlbumsLoading.value = true
    const { data } = await getMusicNewAlbums({ page: 1, page_size: 30 })
    newAlbumsLoading.value = false
    newAlbums.value = data?.items || []
  }

  async function loadNewAlbumsForView() {
    newAlbumsLoading.value = true
    const { data } = await getMusicNewAlbums({ page: 1, page_size: 30 })
    newAlbumsLoading.value = false
    newAlbums.value = data?.items || []
  }

  async function loadNewSongs() {
    newSongsLoading.value = true
    const { data } = await getMusicNewSongs({ page: 1, page_size: 50 })
    newSongsLoading.value = false
    newSongs.value = data?.items || []
  }

  async function loadHotSearches() {
    const { data } = await getMusicHotSearch()
    hotSearches.value = (data?.items || []).slice(0, 12) as MusicHotSearch[]
  }

  async function loadAiRecommend() {
    aiRecommendLoading.value = true
    const { data } = await getMusicAiRecommend({ page_size: 30 })
    aiRecommendLoading.value = false
    aiRecommend.value = data?.items || []
  }

  async function loadEverydayRecommend() {
    everydayRecommendLoading.value = true
    const { data } = await getMusicEverydayRecommend()
    everydayRecommendLoading.value = false
    everydayRecommend.value = data?.items || []
  }

  async function handleSelectPlaylistCategory(categoryId: number) {
    selectedPlaylistCategory.value = categoryId
    await loadPlaylists()
  }

  async function handleLoadMorePlaylists() {
    if (playlistsLoading.value || !playlistHasMore.value) return
    playlistsLoading.value = true
    const { data } = await getMusicPlaylists({
      category_id: selectedPlaylistCategory.value,
      page: 2,
      page_size: 20,
    })
    playlistsLoading.value = false
    if (data?.items?.length) {
      playlists.value = [...playlists.value, ...data.items]
      playlistHasMore.value = data.has_more || false
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
