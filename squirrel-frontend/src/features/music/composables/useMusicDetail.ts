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
} from '@/shared/api/music'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import { Logger } from '@/shared/lib/logger'

type TrackPage = { items: MusicTrack[]; total: number }

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
    try {
      const data = await getMusicFavoriteCount(ids.join(','))
      if (data?.items) {
        const counts: Record<string, number> = { ...favoriteCounts.value }
        for (const item of data.items) {
          if (item.mixsongid) {
            counts[item.mixsongid] = item.count
          }
        }
        favoriteCounts.value = counts
      }
    } catch (err) {
      Logger.warn('loadFavoriteCounts failed', err)
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
    try {
      const [tracksData, similarData] = await Promise.all([
        getMusicPlaylistTracks({ playlist_id: playlist.id, page: 1, page_size: 30 }),
        getMusicSimilarPlaylists(playlist.id).catch((err: unknown) => {
          Logger.warn('selectPlaylist similar failed', err)
          return [] as MusicPlaylist[]
        }),
      ]) as [TrackPage, MusicPlaylist[]]

      tracks.value = tracksData?.items || []
      total.value = tracksData?.total || 0
      tracksHasMore.value = tracks.value.length < total.value
      similarPlaylists.value = (similarData || []).slice(0, 6)

      loadFavoriteCounts(tracks.value)
    } catch (err) {
      Logger.warn('selectPlaylist failed', err)
      tracks.value = []
    } finally {
      tracksLoading.value = false
    }
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
    try {
      const data = await getMusicUserPlaylistTracks({ list_id: playlist.id, page: 1, page_size: 30 }) as TrackPage
      tracks.value = data?.items || []
      total.value = data?.total || 0
      tracksHasMore.value = tracks.value.length < total.value

      loadFavoriteCounts(tracks.value)
    } catch (err) {
      Logger.warn('selectUserPlaylist failed', err)
      tracks.value = []
      total.value = 0
      tracksHasMore.value = false
    } finally {
      tracksLoading.value = false
    }
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
    try {
      // Each sub-fetch is isolated so one failing (e.g. videos) doesn't abort
      // the whole artist view — a missing section just renders empty.
      const [tracksData, albumsData, videosData] = await Promise.all([
        getMusicArtistTracks({ artist_id: artist.id, page: 1, page_size: 30 }).catch((err: unknown) => {
          Logger.warn('selectArtistDetail tracks failed', err)
          return null
        }),
        getMusicArtistAlbums({ artist_id: artist.id, page: 1, page_size: 6 }).catch((err: unknown) => {
          Logger.warn('selectArtistDetail albums failed', err)
          return null
        }),
        getMusicArtistVideos({ artist_id: artist.id, page: 1, page_size: 4 }).catch((err: unknown) => {
          Logger.warn('selectArtistDetail videos failed', err)
          return null
        }),
      ]) as [TrackPage | null, { items: MusicAlbum[] } | null, { items: MusicVideo[] } | null]

      tracks.value = tracksData?.items || []
      total.value = tracksData?.total || 0
      tracksHasMore.value = tracks.value.length < total.value
      artistAlbums.value = albumsData?.items || []
      artistVideos.value = videosData?.items || []
      artistFollowed.value = false

      loadFavoriteCounts(tracks.value)
    } catch (err) {
      Logger.warn('selectArtistDetail failed', err)
      tracks.value = []
    } finally {
      tracksLoading.value = false
    }
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
    try {
      const data = await getMusicAlbumTracks({ album_id: album.id, page: 1, page_size: 30 }) as TrackPage
      tracks.value = data?.items || []
      total.value = data?.total || 0
      tracksHasMore.value = tracks.value.length < total.value

      loadFavoriteCounts(tracks.value)
    } catch (err) {
      Logger.warn('selectAlbum failed', err)
      tracks.value = []
      total.value = 0
      tracksHasMore.value = false
    } finally {
      tracksLoading.value = false
    }
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
    try {
      const data = await getMusicRankTracks({
        rank_id: rank.id,
        rank_cid: rank.rank_cid || undefined,
        page: 1,
        page_size: 50,
      }) as TrackPage
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
    } catch (err) {
      Logger.warn('selectRankAsPlaylist failed', err)
      tracks.value = []
      total.value = 0
      tracksHasMore.value = false
    } finally {
      tracksLoading.value = false
    }
  }

  async function loadMoreTracks() {
    if (tracksLoadingMore.value || !tracksHasMore.value) return

    currentPage.value++
    tracksLoadingMore.value = true

    try {
      let data: TrackPage | null = null

      if (selectedRank.value) {
        data = await getMusicRankTracks({
          rank_id: selectedRank.value.id,
          rank_cid: selectedRank.value.rank_cid || undefined,
          page: currentPage.value,
          page_size: 30,
        }) as TrackPage
      } else if (selectedPlaylist.value) {
        data = await getMusicPlaylistTracks({
          playlist_id: selectedPlaylist.value.id,
          page: currentPage.value,
          page_size: 30,
        }) as TrackPage
      } else if (selectedUserPlaylist.value) {
        data = await getMusicUserPlaylistTracks({
          list_id: selectedUserPlaylist.value.id,
          page: currentPage.value,
          page_size: 30,
        }) as TrackPage
      } else if (selectedArtist.value) {
        data = await getMusicArtistTracks({
          artist_id: selectedArtist.value.id,
          page: currentPage.value,
          page_size: 30,
        }) as TrackPage
      } else if (selectedAlbum.value) {
        data = await getMusicAlbumTracks({
          album_id: selectedAlbum.value.id,
          page: currentPage.value,
          page_size: 30,
        }) as TrackPage
      }

      if (data?.items?.length) {
        tracks.value = [...tracks.value, ...data.items]
        tracksHasMore.value = tracks.value.length < (data.total || 0)
        loadFavoriteCounts(data.items)
      }
    } catch (err) {
      Logger.warn('loadMoreTracks failed', err)
    } finally {
      tracksLoadingMore.value = false
    }
  }

  async function collectPlaylist() {
    if (!selectedPlaylist.value?.id) return false
    try {
      await getMusicSimilarPlaylists(selectedPlaylist.value.id)
      playlistCollected.value = true
      return true
    } catch (err) {
      Logger.warn('collectPlaylist failed', err)
      return false
    }
  }

  async function followArtist() {
    if (!selectedArtist.value?.id) return
    artistFollowLoading.value = true
    try {
      await followMusicArtist(selectedArtist.value.id)
      artistFollowed.value = true
    } catch (err) {
      Logger.warn('followArtist failed', err)
    } finally {
      artistFollowLoading.value = false
    }
  }

  async function unfollowArtist() {
    if (!selectedArtist.value?.id) return
    artistFollowLoading.value = true
    try {
      await unfollowMusicArtist(selectedArtist.value.id)
      artistFollowed.value = false
    } catch (err) {
      Logger.warn('unfollowArtist failed', err)
    } finally {
      artistFollowLoading.value = false
    }
  }

  async function selectArtistFromTrack(track: MusicTrack) {
    if (!track.artist_id) return null
    try {
      const data = await getMusicArtistDetail(track.artist_id)
      if (data) {
        await selectArtistDetail(data)
        return data
      }
      return null
    } catch (err) {
      Logger.warn('selectArtistFromTrack failed', err)
      return null
    }
  }

  async function selectAlbumFromTrack(track: MusicTrack) {
    if (!track.album_id) return null
    try {
      const data = await getMusicAlbumDetail(track.album_id)
      if (data) {
        await selectAlbum(data)
        return data
      }
      return null
    } catch (err) {
      Logger.warn('selectAlbumFromTrack failed', err)
      return null
    }
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
