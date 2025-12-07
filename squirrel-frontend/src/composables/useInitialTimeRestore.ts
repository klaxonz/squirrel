import { watch, onUnmounted, type Ref } from 'vue'
import type { PlayerStore } from '../stores/playerStore'
import type { VideoPlayerCoreInstance } from './usePlayerContext'

export interface UseInitialTimeRestoreOptions {
  store: PlayerStore
  videoCoreRef: Ref<VideoPlayerCoreInstance | null>
  getInitialTime: () => number
  getVideoId: () => string | undefined
}

export default function useInitialTimeRestore({
  store,
  videoCoreRef,
  getInitialTime,
  getVideoId
}: UseInitialTimeRestoreOptions): void {
  let appliedInitialTime = false
  let applyRetryTimer: ReturnType<typeof setTimeout> | null = null
  let applyRetryCount = 0

  const tryApplyInitialTime = (): void => {
    if (appliedInitialTime) return
    const time = Number(getInitialTime?.() || 0)
    if (!(time > 0)) return

    const videoEl = videoCoreRef?.value?.videoElement
    if (!videoEl) return

    const durationReady = Number(store.duration || videoEl.duration || 0) > 0
    const canPlay = store.canPlayVideo
    if (!canPlay || !durationReady) return

    try {
      videoEl.currentTime = time
      const verifyAndMaybeRetry = (): void => {
        if (appliedInitialTime) return
        const current = Number(videoEl.currentTime || 0)
        if (Math.abs(current - time) <= 0.5) {
          appliedInitialTime = true
          return
        }
        if (applyRetryCount < 5) {
          applyRetryCount += 1
          try { videoEl.currentTime = time } catch (e) {}
          applyRetryTimer = setTimeout(verifyAndMaybeRetry, 200)
        } else {
          appliedInitialTime = true
        }
      }
      applyRetryCount = 0
      applyRetryTimer = setTimeout(verifyAndMaybeRetry, 100)
    } catch (e) {}
  }

  watch(() => store.canPlayVideo, () => { tryApplyInitialTime() })
  watch(() => store.duration, () => { tryApplyInitialTime() })
  watch(() => getInitialTime?.(), () => { tryApplyInitialTime() })

  watch(() => getVideoId?.(), () => {
    appliedInitialTime = false
    applyRetryCount = 0
    if (applyRetryTimer) {
      clearTimeout(applyRetryTimer)
      applyRetryTimer = null
    }
  })

  onUnmounted(() => {
    if (applyRetryTimer) {
      clearTimeout(applyRetryTimer)
      applyRetryTimer = null
    }
  })
}
