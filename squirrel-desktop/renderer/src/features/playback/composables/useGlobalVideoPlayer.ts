import { nextTick } from 'vue'
import { usePlayerStore } from '@/features/playback/stores/player'
import { usePlaybackSession } from '@/features/playback/composables/usePlaybackSession'
import type { IPlayerAdapter } from '@/features/playback/components/video-player/core'
import type { PlayerHandlers, VideoPlayerHandle } from '@/features/playback/types/playerSession'
import { Logger } from '@/shared/lib/logger'

// ADR-0002 PR2 — the facts-layer facade verbs
// (`activateGlobalVideoPlayerSession` / `updateGlobalVideoPlayerSession` /
// `clearGlobalVideoPlayerSession` / `globalVideoPlayerSession`) are gone. With
// the shell's 16-source watcher deleted, there is nothing for them to route:
// the orchestrator writes facts directly via `session.update()` /
// `session.beginNewVideo()`, and the shell calls `session.release()` on unmount.
// What remains here are the wiring + utility helpers GlobalVideoPlayerHost and
// the shell still need: target registration, player focus/seek/play, and a
// `publishWiring` helper that publishes the adapter + handler bag onto the
// slimmed Pinia store (which the host reads). ponytail: PR3 relocates the
// adapter/handler wiring into the host itself.

export function useGlobalVideoPlayer() {
  const playerStore = usePlayerStore()
  const session = usePlaybackSession()

  // Wiring publication. The host reads `playerStore.adapter` / `handlers` to
  // mount VideoPlayer; the shell assembles them from view callbacks + the
  // LocalStorageAdapter. This is the seam between the two. ponytail: PR3 folds
  // it into the host (the orchestrator becomes the direct emit target).
  const publishWiring = (handlers: PlayerHandlers, adapter?: IPlayerAdapter | null) => {
    if (adapter !== undefined) playerStore.adapter = adapter ?? null
    playerStore.handlers = handlers
  }

  const registerGlobalVideoPlayerTarget = (element: HTMLElement | null) => {
    playerStore.target = element
  }

  const unregisterGlobalVideoPlayerTarget = (element: HTMLElement | null = null) => {
    if (!element || playerStore.target === element) {
      playerStore.target = null
    }
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
    session,
    registerGlobalVideoPlayerTarget,
    unregisterGlobalVideoPlayerTarget,
    registerGlobalVideoPlayerInstance: (instance: VideoPlayerHandle | null) => { playerStore.playerRef = instance },
    focusGlobalVideoPlayer: focusPlayer,
    seekGlobalVideoPlayer: seekPlayer,
    playGlobalVideoPlayer: playPlayer,
    publishGlobalVideoPlayerWiring: publishWiring,
  }
}
