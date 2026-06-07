import { nextTick } from 'vue'
import { usePlayerStore } from '@/stores/player'
import type { PlayerSessionState } from '@/types/playerSession'

export function useGlobalVideoPlayer() {
  const playerStore = usePlayerStore()

  const activateGlobalVideoPlayerSession = (payload: Partial<PlayerSessionState>) => {
    playerStore.activateSession(payload)
  }

  const updateGlobalVideoPlayerSession = (payload: Partial<PlayerSessionState>) => {
    Object.assign(playerStore.session, payload)
  }

  const registerGlobalVideoPlayerTarget = (element: HTMLElement | null) => {
    playerStore.session.target = element
  }

  const unregisterGlobalVideoPlayerTarget = (element: HTMLElement | null = null) => {
    if (!element || playerStore.session.target === element) {
      playerStore.session.target = null
    }
  }

  const setGlobalVideoPlayerPictureInPicture = (value: unknown) => {
    playerStore.session.pictureInPicture = !!value
  }

  const setGlobalVideoPlayerCurrentVideoId = (videoId: string | number) => {
    playerStore.session.currentVideoId = String(videoId || '')
  }

  const focusPlayer = async () => {
    await nextTick()
    window.setTimeout(() => {
      try {
        const rootEl = playerStore.playerRef?.$el
        const containerEl = rootEl instanceof HTMLElement ? rootEl : null
        const playerContainer = containerEl?.classList?.contains('sp-player')
          ? containerEl
          : containerEl?.querySelector('.sp-player')

        if (playerContainer && typeof (playerContainer as HTMLElement).focus === 'function') {
          (playerContainer as HTMLElement).focus({ preventScroll: true })
        }
      } catch {}
    }, 100)
  }

  const seekPlayer = async (time: number) => {
    const nextTime = Number(time)
    if (!Number.isFinite(nextTime)) return false
    try {
      playerStore.playerRef?.seek?.(nextTime)
      return true
    } catch {
      return false
    }
  }

  const playPlayer = async () => {
    try {
      await playerStore.playerRef?.play?.()
      return true
    } catch {
      return false
    }
  }

  return {
    globalVideoPlayerSession: playerStore.session,
    activateGlobalVideoPlayerSession,
    updateGlobalVideoPlayerSession,
    clearGlobalVideoPlayerSession: playerStore.clearSession,
    registerGlobalVideoPlayerTarget,
    unregisterGlobalVideoPlayerTarget,
    registerGlobalVideoPlayerInstance: (instance: unknown) => { playerStore.playerRef = instance },
    focusGlobalVideoPlayer: focusPlayer,
    seekGlobalVideoPlayer: seekPlayer,
    playGlobalVideoPlayer: playPlayer,
    setGlobalVideoPlayerPictureInPicture,
    setGlobalVideoPlayerCurrentVideoId,
  }
}
