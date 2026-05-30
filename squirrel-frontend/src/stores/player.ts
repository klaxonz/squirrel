import { defineStore } from 'pinia'
import { reactive, shallowRef } from 'vue'

export type PlaylistEntry = {
  id: string
  title: string
  thumbnail?: string
  source: any
  subtitles?: any[]
  clipMarkers?: any[]
  videoId?: string | number
  duration?: number
}

export type PlayerHandlers = {
  onPlay?: (() => void) | null
  onPause?: (() => void) | null
  onEnded?: ((event?: any) => void | Promise<void>) | null
  onTimeUpdate?: ((currentTime: number) => void) | null
  onPrev?: (() => void | Promise<void>) | null
  onNext?: (() => void | Promise<void>) | null
  onRetry?: (() => void | Promise<void>) | null
  onWidescreenChange?: ((enabled: boolean) => void) | null
  onClipMarkerSelect?: ((time: number) => void | Promise<void>) | null
  onClipMarkersUpdated?: ((markers: any[]) => void) | null
}

export const usePlayerStore = defineStore('player', () => {
  const session = reactive({
    active: false,
    target: null as HTMLElement | null,
    source: null as any,
    subtitles: [] as any[],
    clipMarkers: [] as any[],
    title: '',
    uploader: '',
    initialTime: 0,
    hasPrev: false,
    hasNext: false,
    externalError: null as any,
    externalLoading: false,
    adapter: null as any,
    theme: 'dark' as string,
    widescreen: false,
    currentVideoId: '',
    videoSnapshot: null as any,
    relatedVideos: [] as any[],
    loadingRelated: false,
    pictureInPicture: false,
    handlers: {} as PlayerHandlers,
    playlist: [] as PlaylistEntry[],
    playlistIndex: -1,
  })

  const playerRef = shallowRef<any>(null)

  const activateSession = (payload: any = {}) => {
    Object.assign(session, payload)
    session.active = true
  }

  const clearSession = () => {
    session.active = false
    session.target = null
    playerRef.value = null
    session.handlers = {}
  }

  return {
    session,
    playerRef,
    activateSession,
    clearSession
  }
})
