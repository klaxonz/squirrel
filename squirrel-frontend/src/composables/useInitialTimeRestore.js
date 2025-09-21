import { watch, onUnmounted } from 'vue'

// 从上次进度恢复：媒体可播放且时长就绪后应用 initialTime，
// 针对 HLS/DASH 可能的内部重置加入短暂重试。
export default function useInitialTimeRestore({
  playerState,
  videoCoreRef,
  getInitialTime,   // () => number
  getVideoId        // () => any (用于切换视频时重置)
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

    // 要求元数据（时长）已可用，且视频可播放
    const durationReady = Number(playerState.media.duration || videoEl.duration || 0) > 0
    const canPlay = !!playerState.media.canPlay.video
    if (!canPlay || !durationReady) return

    try {
      // 调用宿主提供的同步方法设置时间（VideoPlayer 中提供）
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

  // 媒体可播放或时长就绪时尝试应用
  watch(() => playerState.media.canPlay.video, () => { tryApplyInitialTime() })
  watch(() => playerState.media.duration, () => { tryApplyInitialTime() })

  // 初始时间变化时（例如异步详情加载后）尝试应用
  watch(() => getInitialTime?.(), () => { tryApplyInitialTime() })

  // 切换视频时重置
  watch(() => getVideoId?.(), () => {
    appliedInitialTime = false
    applyRetryCount = 0
    if (applyRetryTimer) { clearTimeout(applyRetryTimer); applyRetryTimer = null }
  })

  onUnmounted(() => {
    if (applyRetryTimer) { clearTimeout(applyRetryTimer); applyRetryTimer = null }
  })
}


