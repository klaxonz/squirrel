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
  getMusicVipClaimStatus,
  claimMusicDailyVip,
  type MusicAuthStatus,
  type MusicUserProfile,
  type MusicUserPlaylist,
  type MusicTrack,
  type MusicVipClaimStatus,
} from '@/shared/api/music'
import { Logger } from '@/shared/lib/logger'
import { isApiError } from '@/shared/lib/apiError'

const VIP_CLAIM_STORAGE_PREFIX = 'music.vipClaimedDay'
const todayIsoDate = () => new Date().toISOString().slice(0, 10)
const vipClaimStorageKey = (userid?: string) => `${VIP_CLAIM_STORAGE_PREFIX}:${userid || 'unknown'}`

const hasLocalVipClaim = (userid?: string) => {
  if (typeof localStorage === 'undefined') return false
  return localStorage.getItem(vipClaimStorageKey(userid)) === todayIsoDate()
}

const rememberLocalVipClaim = (userid?: string) => {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(vipClaimStorageKey(userid), todayIsoDate())
}

const withLocalVipClaim = (status: MusicVipClaimStatus, userid?: string): MusicVipClaimStatus => {
  if (!hasLocalVipClaim(userid)) return status
  return {
    ...status,
    received_today: true,
    receive_day: status.receive_day || todayIsoDate(),
  }
}

const cleanMusicErrorMessage = (message: string) => {
  const cleaned = message
    .replace(/^Error invoking remote method '[^']+':\s*/i, '')
    .replace(/^Error:\s*/i, '')
    .trim()
  return cleaned || message.trim()
}

const musicErrorMessage = (err: unknown, fallback: string) => {
  const message = isApiError(err)
    ? err.message
    : err instanceof Error && err.message
      ? err.message
      : ''
  return message ? cleanMusicErrorMessage(message) : fallback
}

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
  const vipClaimStatus = ref<MusicVipClaimStatus | null>(null)
  const vipClaimLoading = ref(false)
  const vipClaimError = ref('')
  const vipClaimMessage = ref('')
  const profileRankType = ref<0 | 1>(1)

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
        targetUserPlaylistId.value = String(userPlaylists.value[0].listid || '')
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

    const contentLoads = [
      loadUserPlaylists(),
      loadProfileHistory(),
      loadProfileListenRank(),
      loadVipClaimStatus(),
    ]

    try {
      const data = await getMusicUserProfile()
      kugouProfile.value = data || null
    } catch (err) {
      profileError.value = isApiError(err) ? err.message : '加载失败'
      kugouProfile.value = null
    } finally {
      profileLoading.value = false
    }

    await Promise.allSettled(contentLoads)
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

  async function loadVipClaimStatus() {
    if (!authStatus.value?.logged_in) return
    try {
      vipClaimError.value = ''
      const data = await getMusicVipClaimStatus()
      vipClaimStatus.value = withLocalVipClaim(data, authStatus.value?.userid)
    } catch (err) {
      Logger.warn('loadVipClaimStatus failed', err)
      vipClaimError.value = musicErrorMessage(err, '签到状态加载失败')
      vipClaimStatus.value = null
    }
  }

  async function claimDailyVip() {
    if (!authStatus.value?.logged_in || vipClaimLoading.value || vipClaimStatus.value?.received_today) return
    vipClaimLoading.value = true
    vipClaimError.value = ''
    vipClaimMessage.value = ''
    try {
      const data = await claimMusicDailyVip()
      if (data?.received_today) rememberLocalVipClaim(authStatus.value?.userid)
      vipClaimStatus.value = data?.received_today
        ? withLocalVipClaim(data, authStatus.value?.userid)
        : data
      vipClaimMessage.value = data?.message || (data?.received_today ? '领取成功' : '')
    } catch (err) {
      Logger.warn('claimDailyVip failed', err)
      vipClaimError.value = musicErrorMessage(err, '领取失败，请稍后重试')
    } finally {
      vipClaimLoading.value = false
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
    vipClaimStatus.value = null
    vipClaimMessage.value = ''
    vipClaimError.value = ''
  }

  async function createPlaylist(name: string): Promise<boolean> {
    try {
      await createMusicUserPlaylist({ name, is_private: false })
      await loadUserPlaylists()
      return true
    } catch (err) {
      Logger.warn('createPlaylist failed', err)
      return false
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
      loadVipClaimStatus()
    } else {
      userPlaylists.value = []
      kugouProfile.value = null
      vipClaimStatus.value = null
      vipClaimMessage.value = ''
      vipClaimError.value = ''
    }
  })

  return {
    authStatus, kugouProfile, userPlaylists, targetUserPlaylistId,
    profileLoading, profileError, logoutLoading,
    profileHistory, profileListenRank, profileHistoryLoading, profileRankLoading,
    vipClaimStatus, vipClaimLoading, vipClaimError, vipClaimMessage, profileRankType,
    loadAuthStatus, loadProfile, loadProfileHistory, loadProfileListenRank,
    loadVipClaimStatus, claimDailyVip,
    toggleRankType, logout, createPlaylist, addToPlaylist,
  }
}
