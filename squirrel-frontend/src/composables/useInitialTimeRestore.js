import { watch, onUnmounted } from 'vue'

// 从上次进度恢复
// store: Pinia player store
// videoCoreRef: ref to video core component
// getInitialTime: () => number
// getVideoId: () => any
export default function useInitialTimeRestore({
  store,
  videoCoreRef,
  getInitialTime,
  getVideoId
}) {
  let appliedInitialTime = false
  let applyRetryTimer = null
  let applyRetryCount = 0

  const tryApplyInitialTime = () => {
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
      const verifyAndMaybeRetry = () => {
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
    if (applyRetryTimer) { clearTimeout(applyRetryTimer); applyRetryTimer = null }
  })

  onUnmounted(() => {
    if (applyRetryTimer) { clearTimeout(applyRetryTimer); applyRetryTimer = null }
  })
}
