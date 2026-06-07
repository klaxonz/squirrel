import { defineStore } from 'pinia'
import { reactive, shallowRef } from 'vue'
import type { PlayerSessionState, PlaylistEntry, PlayerHandlers } from '@/types/playerSession'

export type { PlaylistEntry, PlayerHandlers }

export const usePlayerStore = defineStore('player', () => {
  const session: PlayerSessionState = reactive({
    active: false,
    target: null,
    source: null,
    subtitles: [],
    clipMarkers: [],
    title: '',
    uploader: '',
    initialTime: 0,
    hasPrev: false,
    hasNext: false,
    externalError: null,
    externalLoading: false,
    adapter: null,
    theme: 'dark',
    widescreen: false,
    currentVideoId: '',
    videoSnapshot: null,
    relatedVideos: [],
    loadingRelated: false,
    pictureInPicture: false,
    handlers: {} as PlayerHandlers,
    playlist: [],
    playlistIndex: -1,
  })

  const playerRef = shallowRef<any>(null)

  const activateSession = (payload: Partial<PlayerSessionState>) => {
    Object.assign(session, payload)
    session.active = true
  }

  const clearSession = () => {
    session.active = false
    session.target = null
    playerRef.value = null
    session.handlers = {} as PlayerHandlers
  }

  return {
    session,
    playerRef,
    activateSession,
    clearSession
  }
})
