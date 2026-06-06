import { ref, computed } from 'vue'
import {
  getMusicPlaylistTracks,
  getMusicSimilarPlaylists,
  getMusicUserPlaylistTracks,
  getMusicArtistDetail,
  getMusicArtistTracks,
  getMusicArtistAlbums,
  getMusicArtistVideos,
  getMusicAlbumDetail,
  getMusicAlbumTracks,
  getMusicFavoriteCount,
  getMusicRankTracks,
  followMusicArtist,
  unfollowMusicArtist,
  type MusicTrack,
  type MusicPlaylist,
  type MusicRank,
  type MusicArtist,
  type MusicAlbum,
  type MusicUserPlaylist,
  type MusicVideo,
} from '@/api/music'
import { useMusicPlayerStore } from '@/stores/musicPlayer'

export function useMusicDetail() {
  const store = useMusicPlayerStore()

  const selectedPlaylist = ref<MusicPlaylist | null>(null)
  const selectedUserPlaylist = ref<MusicUserPlaylist | null>(null)
  const selectedArtist = ref<MusicArtist | null>(null)
  const selectedAlbum = ref<MusicAlbum | null>(null)
  const selectedRank = ref<MusicRank | null>(null)
  const tracks = ref<MusicTrack[]>([])
  const tracksLoading = ref(false)
  const tracksLoadingMore = ref(false)
  const tracksHasMore = ref(false)
  const total = ref(0)
  const currentPage = ref(1)
  const similarPlaylists = ref<MusicPlaylist[]>([])
  const artistAlbums = ref<MusicAlbum[]>([])
  const artistVideos = ref<MusicVideo[]>([])
  const artistFollowed = ref(false)
  const artistFollowLoading = ref(false)
  const playlistCollected = ref(false)
  const favoriteCounts = ref<Record<string, number>>({})

  const userPlaylistAsPlaylist = computed(() => {
    if (!selectedUserPlaylist.value) return null
    const pl = selectedUserPlaylist.value
    return {
      id: pl.id,
      name: pl.name,
      cover: pl.cover,
      intro: '',
      creator: '',
      play_count: 0,
      collect_count: 0,
      tags: [],
      list_create_userid: pl.list_create_userid,
      list_create_listid: pl.list_create_listid,
      list_create_gid: pl.list_create_gid,
    } as MusicPlaylist
  })

  async function loadFavoriteCounts(trackList: MusicTrack[]) {
    const ids = trackList.map(t => t.album_audio_id).filter(Boolean)
    if (!ids.length) return
    const { data } = await getMusicFavoriteCount(ids.join(','))
    if (data?.items) {
      const counts: Record<string, number> = { ...favoriteCounts.value }
      for (const item of data.items) {
        if (item.mixsongid) {
          counts[item.mixsongid] = item.count
        }
      }
      favoriteCounts.value = counts
    }
  }

  async function selectPlaylist(playlist: MusicPlaylist) {
    selectedPlaylist.value = playlist
    selectedUserPlaylist.value = null
    selectedArtist.value = null
    selectedAlbum.value = null
    selectedRank.value = null
    currentPage.value = 1
    tracks.value = []

    tracksLoading.value = true
    const [tracksData, similarData] = await Promise.all([
      getMusicPlaylistTracks({ playlist_id: playlist.id, page: 1, page_size: 30 }),
      getMusicSimilarPlaylists(playlist.id),
    ])
    tracksLoading.value = false

    tracks.value = tracksData.data?.items || []
    total.value = tracksData.data?.total || 0
    tracksHasMore.value = tracks.value.length < total.value
    similarPlaylists.value = (similarData.data?.items || []).slice(0, 6)

    loadFavoriteCounts(tracks.value)
  }

  async function selectUserPlaylist(playlist: MusicUserPlaylist) {
    selectedUserPlaylist.value = playlist
    selectedPlaylist.value = null
    selectedArtist.value = null
    selectedAlbum.value = null
    selectedRank.value = null
    currentPage.value = 1
    tracks.value = []

    tracksLoading.value = true
    const { data } = await getMusicUserPlaylistTracks({ list_id: playlist.id, page: 1, page_size: 30 })
    tracksLoading.value = false

    tracks.value = data?.items || []
    total.value = data?.total || 0
    tracksHasMore.value = tracks.value.length < total.value

    loadFavoriteCounts(tracks.value)
  }

  async function selectArtistDetail(artist: MusicArtist) {
    selectedArtist.value = artist
    selectedPlaylist.value = null
    selectedUserPlaylist.value = null
    selectedAlbum.value = null
    selectedRank.value = null
    currentPage.value = 1
    tracks.value = []

    tracksLoading.value = true
    const [tracksData, albumsData, videosData] = await Promise.all([
      getMusicArtistTracks({ artist_id: artist.id, page: 1, page_size: 30 }),
      getMusicArtistAlbums({ artist_id: artist.id, page: 1, page_size: 6 }),
      getMusicArtistVideos({ artist_id: artist.id, page: 1, page_size: 4 }),
    ])
    tracksLoading.value = false

    tracks.value = tracksData.data?.items || []
    total.value = tracksData.data?.total || 0
    tracksHasMore.value = tracks.value.length < total.value
    artistAlbums.value = albumsData.data?.items || []
    artistVideos.value = videosData.data?.items || []
    artistFollowed.value = false

    loadFavoriteCounts(tracks.value)
  }

  async function selectAlbum(album: MusicAlbum) {
    selectedAlbum.value = album
    selectedPlaylist.value = null
    selectedUserPlaylist.value = null
    selectedArtist.value = null
    selectedRank.value = null
    currentPage.value = 1
    tracks.value = []

    tracksLoading.value = true
    const { data } = await getMusicAlbumTracks({ album_id: album.id, page: 1, page_size: 30 })
    tracksLoading.value = false

    tracks.value = data?.items || []
    total.value = data?.total || 0
    tracksHasMore.value = tracks.value.length < total.value

    loadFavoriteCounts(tracks.value)
  }

  async function selectRankAsPlaylist(rank: MusicRank) {
    selectedPlaylist.value = null
    selectedUserPlaylist.value = null
    selectedArtist.value = null
    selectedAlbum.value = null
    selectedRank.value = rank
    tracks.value = []
    currentPage.value = 1

    tracksLoading.value = true
    const { data } = await getMusicRankTracks({
      rank_id: rank.id,
      rank_cid: rank.rank_cid || undefined,
      page: 1,
      page_size: 50,
    })
    tracksLoading.value = false

    tracks.value = data?.items || []
    total.value = data?.total || 0
    tracksHasMore.value = tracks.value.length < total.value

    selectedPlaylist.value = {
      id: rank.id,
      name: rank.name,
      cover: rank.cover,
      intro: rank.intro || '',
      creator: '',
      play_count: rank.play_count || 0,
      collect_count: 0,
      tags: [],
      list_create_userid: '',
      list_create_listid: '',
      list_create_gid: '',
    }
  }

  async function loadMoreTracks() {
    if (tracksLoadingMore.value || !tracksHasMore.value) return

    currentPage.value++
    tracksLoadingMore.value = true

    let data: { items: MusicTrack[]; total: number } | null = null

    if (selectedRank.value) {
      const result = await getMusicRankTracks({
        rank_id: selectedRank.value.id,
        rank_cid: selectedRank.value.rank_cid || undefined,
        page: currentPage.value,
        page_size: 30,
      })
      data = result.data
    } else if (selectedPlaylist.value) {
      const result = await getMusicPlaylistTracks({
        playlist_id: selectedPlaylist.value.id,
        page: currentPage.value,
        page_size: 30,
      })
      data = result.data
    } else if (selectedUserPlaylist.value) {
      const result = await getMusicUserPlaylistTracks({
        list_id: selectedUserPlaylist.value.id,
        page: currentPage.value,
        page_size: 30,
      })
      data = result.data
    } else if (selectedArtist.value) {
      const result = await getMusicArtistTracks({
        artist_id: selectedArtist.value.id,
        page: currentPage.value,
        page_size: 30,
      })
      data = result.data
    } else if (selectedAlbum.value) {
      const result = await getMusicAlbumTracks({
        album_id: selectedAlbum.value.id,
        page: currentPage.value,
        page_size: 30,
      })
      data = result.data
    }

    tracksLoadingMore.value = false

    if (data?.items?.length) {
      tracks.value = [...tracks.value, ...data.items]
      tracksHasMore.value = tracks.value.length < (data.total || 0)
      loadFavoriteCounts(data.items)
    }
  }

  async function collectPlaylist() {
    if (!selectedPlaylist.value?.id) return false
    const { error } = await getMusicSimilarPlaylists(selectedPlaylist.value.id)
    if (!error) {
      playlistCollected.value = true
      return true
    }
    return false
  }

  async function followArtist() {
    if (!selectedArtist.value?.id) return
    artistFollowLoading.value = true
    const { error } = await followMusicArtist(selectedArtist.value.id)
    artistFollowLoading.value = false
    if (!error) artistFollowed.value = true
  }

  async function unfollowArtist() {
    if (!selectedArtist.value?.id) return
    artistFollowLoading.value = true
    const { error } = await unfollowMusicArtist(selectedArtist.value.id)
    artistFollowLoading.value = false
    if (!error) artistFollowed.value = false
  }

  async function selectArtistFromTrack(track: MusicTrack) {
    if (!track.artist_id) return null
    const { data } = await getMusicArtistDetail(track.artist_id)
    if (data) {
      await selectArtistDetail(data)
      return data
    }
    return null
  }

  async function selectAlbumFromTrack(track: MusicTrack) {
    if (!track.album_id) return null
    const { data } = await getMusicAlbumDetail(track.album_id)
    if (data) {
      await selectAlbum(data)
      return data
    }
    return null
  }

  function playAll(shuffle: boolean = false) {
    store.shuffle = shuffle
    store.playQueue(tracks.value, 0)
  }

  function playAllArtistTracks() {
    store.playQueue(tracks.value, 0)
  }

  function clearDetail() {
    selectedPlaylist.value = null
    selectedUserPlaylist.value = null
    selectedArtist.value = null
    selectedAlbum.value = null
    selectedRank.value = null
    tracks.value = []
    currentPage.value = 1
    tracksHasMore.value = false
    similarPlaylists.value = []
    artistAlbums.value = []
    artistVideos.value = []
    artistFollowed.value = false
    playlistCollected.value = false
  }

  return {
    selectedPlaylist, selectedUserPlaylist, selectedArtist, selectedAlbum, selectedRank,
    tracks, tracksLoading, tracksLoadingMore, tracksHasMore, total,
    similarPlaylists, artistAlbums, artistVideos,
    artistFollowed, artistFollowLoading, playlistCollected, favoriteCounts,
    userPlaylistAsPlaylist,
    selectPlaylist, selectUserPlaylist, selectArtistDetail, selectAlbum,
    selectRankAsPlaylist, selectArtistFromTrack, selectAlbumFromTrack,
    loadMoreTracks, collectPlaylist, followArtist, unfollowArtist,
    playAll, playAllArtistTracks, clearDetail,
  }
}
