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
      const { data, error } = await getMusicAuthStatus()
      if (error) {
        Logger.warn('loadAuthStatus failed', error)
        return
      }
      authStatus.value = data || null
      if (data?.logged_in) {
        loadUserPlaylists()
      }
    } catch (err) {
      Logger.warn('loadAuthStatus threw', err)
    }
  }

  async function loadUserPlaylists() {
    try {
      const { data, error } = await getMusicUserPlaylists()
      if (error) {
        Logger.warn('loadUserPlaylists failed', error)
        userPlaylists.value = []
        return
      }
      userPlaylists.value = data?.items || []
      if (userPlaylists.value.length && !targetUserPlaylistId.value) {
        targetUserPlaylistId.value = userPlaylists.value[0].id
      }
    } catch (err) {
      Logger.warn('loadUserPlaylists threw', err)
      userPlaylists.value = []
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
    try {
      const { data, error } = await getMusicUserHistory()
      if (error) {
        Logger.warn('loadProfileHistory failed', error)
        profileHistory.value = []
        return
      }
      profileHistory.value = data?.items || []
    } catch (err) {
      Logger.warn('loadProfileHistory threw', err)
      profileHistory.value = []
    } finally {
      profileHistoryLoading.value = false
    }
  }

  async function loadProfileListenRank() {
    if (!authStatus.value?.logged_in) return
    profileRankLoading.value = true
    try {
      const { data, error } = await getMusicUserListenRank({ type: profileRankType.value })
      if (error) {
        Logger.warn('loadProfileListenRank failed', error)
        profileListenRank.value = []
        return
      }
      profileListenRank.value = data?.items || []
    } catch (err) {
      Logger.warn('loadProfileListenRank threw', err)
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
      const { error } = await logoutMusicUser()
      if (error) Logger.warn('logout failed', error)
    } catch (err) {
      Logger.warn('logout threw', err)
    } finally {
      logoutLoading.value = false
    }
    authStatus.value = null
    kugouProfile.value = null
    userPlaylists.value = []
  }

  async function createPlaylist(name: string) {
    const { error } = await createMusicUserPlaylist({ name, is_private: false })
    if (error) {
      Logger.warn('createPlaylist failed', error)
      return
    }
    loadUserPlaylists()
  }

  async function addToPlaylist(track: MusicTrack) {
    if (!targetUserPlaylistId.value) return
    try {
      const { error } = await addMusicUserPlaylistTrack({
        list_id: targetUserPlaylistId.value,
        track: {
          title: track.title,
          hash: track.hash,
          album_id: track.album_id,
          album_audio_id: track.album_audio_id,
        },
      })
      if (error) Logger.warn('addToPlaylist failed', error)
    } catch (err) {
      Logger.warn('addToPlaylist threw', err)
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
