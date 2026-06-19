import { ref, watch } from 'vue'
import {
  getMusicAuthStatus,
  getMusicUserProfile,
  getMusicUserPlaylists,
  getMusicUserHistory,
  getMusicUserListenRank,
  createMusicUserPlaylist,
  addMusicUserPlaylistTrack,
  logoutMusicUser,
  type MusicAuthStatus,
  type MusicUserProfile,
  type MusicUserPlaylist,
  type MusicTrack,
} from '@/shared/api/music'

export function useMusicAuth() {
  const authStatus = ref<MusicAuthStatus | null>(null)
  const kugouProfile = ref<MusicUserProfile | null>(null)
  const userPlaylists = ref<MusicUserPlaylist[]>([])
  const targetUserPlaylistId = ref('')
  const profileLoading = ref(false)
  const profileError = ref('')
  const logoutLoading = ref(false)
  const profileHistory = ref<MusicTrack[]>([])
  const profileListenRank = ref<MusicTrack[]>([])
  const profileHistoryLoading = ref(false)
  const profileRankLoading = ref(false)
  const profileRankType = ref<0 | 1>(0)

  async function loadAuthStatus() {
    const { data } = await getMusicAuthStatus()
    authStatus.value = data || null
    if (data?.logged_in) {
      loadUserPlaylists()
    }
  }

  async function loadUserPlaylists() {
    const { data } = await getMusicUserPlaylists()
    userPlaylists.value = data?.items || []
    if (userPlaylists.value.length && !targetUserPlaylistId.value) {
      targetUserPlaylistId.value = userPlaylists.value[0].id
    }
  }

  async function loadProfile() {
    if (!authStatus.value?.logged_in) return

    profileLoading.value = true
    profileError.value = ''

    const { data, error } = await getMusicUserProfile()
    profileLoading.value = false

    if (error) {
      profileError.value = error.message
      kugouProfile.value = null
      return
    }

    kugouProfile.value = data || null
    loadProfileHistory()
    loadProfileListenRank()
  }

  async function loadProfileHistory() {
    if (!authStatus.value?.logged_in) return
    profileHistoryLoading.value = true
    const { data } = await getMusicUserHistory()
    profileHistoryLoading.value = false
    profileHistory.value = data?.items || []
  }

  async function loadProfileListenRank() {
    if (!authStatus.value?.logged_in) return
    profileRankLoading.value = true
    const { data } = await getMusicUserListenRank({ type: profileRankType.value })
    profileRankLoading.value = false
    profileListenRank.value = data?.items || []
  }

  function toggleRankType(type: 0 | 1) {
    profileRankType.value = type
    loadProfileListenRank()
  }

  async function logout() {
    logoutLoading.value = true
    await logoutMusicUser()
    logoutLoading.value = false
    authStatus.value = null
    kugouProfile.value = null
    userPlaylists.value = []
  }

  async function createPlaylist(name: string) {
    const { error } = await createMusicUserPlaylist({ name, is_private: false })
    if (!error) {
      loadUserPlaylists()
    }
  }

  async function addToPlaylist(track: MusicTrack) {
    if (!targetUserPlaylistId.value) return
    await addMusicUserPlaylistTrack({
      list_id: targetUserPlaylistId.value,
      track: {
        title: track.title,
        hash: track.hash,
        album_id: track.album_id,
        album_audio_id: track.album_audio_id,
      },
    })
  }

  watch(() => authStatus.value?.logged_in, (loggedIn) => {
    if (loggedIn) {
      loadUserPlaylists()
    } else {
      userPlaylists.value = []
      kugouProfile.value = null
    }
  })

  return {
    authStatus, kugouProfile, userPlaylists, targetUserPlaylistId,
    profileLoading, profileError, logoutLoading,
    profileHistory, profileListenRank, profileHistoryLoading, profileRankLoading, profileRankType,
    loadAuthStatus, loadProfile, loadProfileHistory, loadProfileListenRank,
    toggleRankType, logout, createPlaylist, addToPlaylist,
  }
}
