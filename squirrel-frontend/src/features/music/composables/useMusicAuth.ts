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
import { Logger } from '@/shared/lib/logger'
import { isApiError } from '@/shared/lib/apiError'

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
    try {
      const data = await getMusicAuthStatus()
      authStatus.value = data || null
      if (data?.logged_in) {
        loadUserPlaylists()
      }
    } catch (err) {
      Logger.warn('loadAuthStatus failed', err)
    }
  }

  async function loadUserPlaylists() {
    try {
      const data = await getMusicUserPlaylists()
      userPlaylists.value = data?.items || []
      if (userPlaylists.value.length && !targetUserPlaylistId.value) {
        targetUserPlaylistId.value = userPlaylists.value[0].id
      }
    } catch (err) {
      Logger.warn('loadUserPlaylists failed', err)
      userPlaylists.value = []
    }
  }

  async function loadProfile() {
    if (!authStatus.value?.logged_in) return

    profileLoading.value = true
    profileError.value = ''

    try {
      const data = await getMusicUserProfile()
      kugouProfile.value = data || null
      loadProfileHistory()
      loadProfileListenRank()
    } catch (err) {
      profileError.value = isApiError(err) ? err.message : '加载失败'
      kugouProfile.value = null
    } finally {
      profileLoading.value = false
    }
  }

  async function loadProfileHistory() {
    if (!authStatus.value?.logged_in) return
    profileHistoryLoading.value = true
    try {
      const data = await getMusicUserHistory()
      profileHistory.value = data?.items || []
    } catch (err) {
      Logger.warn('loadProfileHistory failed', err)
      profileHistory.value = []
    } finally {
      profileHistoryLoading.value = false
    }
  }

  async function loadProfileListenRank() {
    if (!authStatus.value?.logged_in) return
    profileRankLoading.value = true
    try {
      const data = await getMusicUserListenRank({ type: profileRankType.value })
      profileListenRank.value = data?.items || []
    } catch (err) {
      Logger.warn('loadProfileListenRank failed', err)
      profileListenRank.value = []
    } finally {
      profileRankLoading.value = false
    }
  }

  function toggleRankType(type: 0 | 1) {
    profileRankType.value = type
    loadProfileListenRank()
  }

  async function logout() {
    logoutLoading.value = true
    try {
      await logoutMusicUser()
    } catch (err) {
      Logger.warn('logout failed', err)
    } finally {
      logoutLoading.value = false
    }
    authStatus.value = null
    kugouProfile.value = null
    userPlaylists.value = []
  }

  async function createPlaylist(name: string) {
    try {
      await createMusicUserPlaylist({ name, is_private: false })
      loadUserPlaylists()
    } catch (err) {
      Logger.warn('createPlaylist failed', err)
    }
  }

  async function addToPlaylist(track: MusicTrack) {
    if (!targetUserPlaylistId.value) return
    try {
      await addMusicUserPlaylistTrack({
        list_id: targetUserPlaylistId.value,
        track: {
          title: track.title,
          hash: track.hash,
          album_id: track.album_id,
          album_audio_id: track.album_audio_id,
        },
      })
    } catch (err) {
      Logger.warn('addToPlaylist failed', err)
    }
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
