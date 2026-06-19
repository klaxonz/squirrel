import { nextTick } from 'vue'
import { usePlayerStore } from '@/stores/player'
import { usePlaybackSession } from './usePlaybackSession'
import type { PlaybackSessionFacts } from './usePlaybackSession'
import type { IPlayerAdapter } from '@/components/video-player/core'
import type { PlayerHandlers, VideoPlayerHandle } from '@/types/playerSession'
import { Logger } from '@/utils/logger'

// ponytail: this composable used to be a thin shim over the old
// `playerStore.session` reactive bag. Per ADR-0002 the facts layer moved to
// PlaybackSession. The public surface (the names VideoPlay /
// useVideoPlaybackShell call) is preserved so PR1 is a structural swap; the
// implementations route to the new owner. The two dead wrappers
// (setGlobalVideoPlayerPictureInPicture / setGlobalVideoPlayerCurrentVideoId)
// were deleted — they had zero callers.

// Payload shape the shell still passes to activate/update. `target` /
// `adapter` / `handlers` are wiring state (PR1 keeps them on the Pinia store,
// PR2 relocates them); the rest are facts routed to PlaybackSession.
export type PlayerSessionPayload = Partial<PlaybackSessionFacts> & {
  target?: HTMLElement | null
  adapter?: IPlayerAdapter | null
  handlers?: PlayerHandlers
}

export function useGlobalVideoPlayer() {
  const playerStore = usePlayerStore()
  const session = usePlaybackSession()

  const applyPayload = (payload: PlayerSessionPayload) => {
    if (payload.target !== undefined) playerStore.target = payload.target ?? null
    if (payload.adapter !== undefined) playerStore.adapter = payload.adapter ?? null
    if (payload.handlers !== undefined) playerStore.handlers = payload.handlers ?? ({} as PlayerHandlers)

    const { target: _t, adapter: _a, handlers: _h, ...facts } = payload
    if (Object.keys(facts).length > 0) session.update(facts)
  }

  const activateGlobalVideoPlayerSession = (payload: PlayerSessionPayload) => {
    applyPayload(payload)
  }

  const updateGlobalVideoPlayerSession = (payload: PlayerSessionPayload) => {
    applyPayload(payload)
  }

  const registerGlobalVideoPlayerTarget = (element: HTMLElement | null) => {
    playerStore.target = element
  }

  const unregisterGlobalVideoPlayerTarget = (element: HTMLElement | null = null) => {
    if (!element || playerStore.target === element) {
      playerStore.target = null
    }
  }

  const clearGlobalVideoPlayerSession = () => {
    // PR1 keeps the PiP-aware semantics on the clear path too, so behavior is
    // byte-identical to the old clearSession (which was only called from the
    // shell's onUnmounted after the PiP check). PR2 collapses this to
    // session.release() at the call site and drops the wiring reset.
    session.release()
    playerStore.playerRef = null
    playerStore.target = null
    playerStore.adapter = null
    playerStore.handlers = {} as PlayerHandlers
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
      } catch (err) {
        Logger.warn('[useGlobalVideoPlayer] Focus player failed', err)
      }
    }, 100)
  }

  const seekPlayer = async (time: number) => {
    const nextTime = Number(time)
    if (!Number.isFinite(nextTime)) return false
    try {
      playerStore.playerRef?.seek?.(nextTime)
      return true
    } catch (err) {
      Logger.warn('[useGlobalVideoPlayer] Seek failed', err)
      return false
    }
  }

  const playPlayer = async () => {
    try {
      await playerStore.playerRef?.play?.()
      return true
    } catch (err) {
      Logger.warn('[useGlobalVideoPlayer] Play failed', err)
      return false
    }
  }

  return {
    globalVideoPlayerSession: session.facts,
    activateGlobalVideoPlayerSession,
    updateGlobalVideoPlayerSession,
    clearGlobalVideoPlayerSession,
    registerGlobalVideoPlayerTarget,
    unregisterGlobalVideoPlayerTarget,
    registerGlobalVideoPlayerInstance: (instance: VideoPlayerHandle | null) => { playerStore.playerRef = instance },
    focusGlobalVideoPlayer: focusPlayer,
    seekGlobalVideoPlayer: seekPlayer,
    playGlobalVideoPlayer: playPlayer,
  }
}

