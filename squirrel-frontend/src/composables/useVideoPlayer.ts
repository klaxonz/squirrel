import { ref, reactive, computed, watch, onMounted, onUnmounted, type Ref, type ComputedRef } from 'vue'
import useVideoHistory from './useVideoHistory'
import useVideoErrorHandler from './useVideoErrorHandler'
import usePerformanceMonitor from './usePerformanceMonitor'
import { usePlayerStore, type PlayerStore } from '../stores/playerStore'
import axios from '../utils/axios'
import type { VideoInfo, ErrorInfo, PerformanceState } from '../types/video-player'
import type { VideoPlayerCoreInstance } from './usePlayerContext'

/**
 * 播放器 Props 接口
 */
export interface VideoPlayerProps {
  video?: VideoInfo & { 
    mpd_url?: string
    stream_video_url?: string
    stream_audio_url?: string
  }
  initialTime?: number
  hasPrev?: boolean
  hasNext?: boolean
  externalError?: any
}

/**
 * 播放器 Emit 函数类型
 */
export interface VideoPlayerEmit {
  (event: 'play'): void
  (event: 'pause'): void
  (event: 'ended', data?: any): void
  (event: 'fullscreenChange', isFullscreen: boolean): void
  (event: 'timeupdate', currentTime: number): void
  (event: 'error', error: { type: string; error: any; errorInfo?: ErrorInfo }): void
  (event: 'prev-video'): void
  (event: 'next-video'): void
}

/**
 * useVideoPlayer 返回类型
 */
export interface UseVideoPlayerReturn {
  store: PlayerStore
  performanceState: PerformanceState
  errorState: any
  videoCore: Ref<VideoPlayerCoreInstance | null>
  isHlsStream: ComputedRef<boolean>
  isDashStream: ComputedRef<boolean>
  hasAudioStream: ComputedRef<boolean>
  isCanplay: ComputedRef<boolean>
  volumeIcon: ComputedRef<string>
  fullscreenIcon: ComputedRef<string>
  progress: ComputedRef<number>
  supportsPiP: ComputedRef<boolean>
  loadingStatusText: ComputedRef<string>
  updateBandwidth: (loaded: number, durationSec: number) => void
  formatNetworkSpeed: (bps: number) => string
  handleVideoPlay: () => void
  handleVideoPause: () => void
  handleVideoTimeupdate: () => void
  handleVideoError: (error: any) => void
  handleVideoLayerClick: () => void
  setVideoTime: (time: number) => void
  getErrorInfo: () => ErrorInfo | null
  handleRetry: () => void
  reportErrorToSupport: () => Promise<void>
  dismissError: () => void
  onPointerEnter: () => void
  onPointerLeave: () => void
  onPointerMove: () => void
}

// 全屏事件名列表
const fullscreenEventNames = [
  'fullscreenchange',
  'webkitfullscreenchange',
  'mozfullscreenchange',
  'MSFullscreenChange'
]

// 速度探测配置
const PROBE_INTERVAL_MS = 1000
const PROBE_CHUNK_BYTES = 128 * 1024
const PROBE_TIMEOUT_MS = 4000

/**
 * 视频播放器核心 Composable
 */
export default function useVideoPlayer(
  props: VideoPlayerProps,
  emit: VideoPlayerEmit
): UseVideoPlayerReturn {
  // DOM 引用
  const videoCore: Ref<VideoPlayerCoreInstance | null> = ref(null)

  // 使用 Pinia store
  const store = usePlayerStore()

  // 性能监控状态
  const performanceState = reactive<PerformanceState>({
    bandwidth: { samples: [], average: 0, current: 0 },
    memory: { used: 0, peak: 0, lastCleanup: 0 },
    loading: { startTime: 0, duration: 0, bytesLoaded: 0 }
  })

  // 组合函数
  const { sendReport, updateLocalHistory } = useVideoHistory()

  const {
    errorState,
    handleError,
    manualRetry,
    clearError,
    getErrorInfo,
    reportError
  } = useVideoErrorHandler()

  const {
    updateBandwidth
  } = usePerformanceMonitor({
    hlsRef: null,
    videoRef: () => videoCore.value?.videoElement || null,
    externalPerformanceState: performanceState
  })

  // 计算属性
  const isHlsStream = computed<boolean>(() =>
    !!props.video?.stream_video_url && props.video.stream_video_url.includes('.m3u8')
  )

  const isDashStream = computed<boolean>(() =>
    !!props.video?.mpd_url || 
    (!!props.video?.stream_video_url && props.video.stream_video_url.endsWith('.mpd'))
  )

  const hasAudioStream = computed<boolean>(() => !!props.video?.stream_audio_url)

  const isCanplay = computed<boolean>(() => {
    if (!hasAudioStream.value) {
      return store.canPlayVideo
    }
    return store.canPlayVideo && (isHlsStream.value || store.canPlayAudio)
  })

  // 直接使用 store 的计算属性
  const volumeIcon = computed<string>(() => store.volumeIcon)
  const fullscreenIcon = computed<string>(() => store.fullscreenIcon)
  const progress = computed<number>(() => store.progress)
  const loadingStatusText = computed<string>(() => store.loadingStatusText)

  const supportsPiP = computed<boolean>(() =>
    !!(document.pictureInPictureEnabled && videoCore.value?.videoElement)
  )

  // 同步全屏状态
  const getPlayerContainer = (): HTMLElement | null => {
    const videoEl = videoCore.value?.videoElement
    if (!videoEl) return null
    let container: HTMLElement | null = videoEl.parentElement
    while (container && !container.classList?.contains('video-player-container')) {
      container = container.parentElement
    }
    return container || null
  }

  const getDocFullscreenElement = (): Element | null => {
    return (
      document.fullscreenElement ||
      (document as any).webkitFullscreenElement ||
      (document as any).mozFullScreenElement ||
      (document as any).msFullscreenElement ||
      null
    )
  }

  const updateFullscreenState = (): void => {
    try {
      const container = getPlayerContainer()
      const fsEl = getDocFullscreenElement()
      const isFs = !!(container && fsEl === container)
      if (store.fullscreen !== isFs) {
        store.setFullscreen(isFs)
        try { 
          emit('fullscreenChange', isFs) 
        } catch (e) {
          // Ignore emit errors
        }
      }
    } catch (e) {
      // Ignore fullscreen state errors
    }
  }

  // 格式化网络速度
  const formatNetworkSpeed = (bps: number): string => {
    if (!bps || bps <= 0) return ''
    const bytesPerSecond = bps / 8
    const mBps = bytesPerSecond / 1024 / 1024
    const kBps = bytesPerSecond / 1024
    if (mBps >= 1) return `${mBps.toFixed(1)} MB/s`
    return `${Math.round(kBps)} KB/s`
  }

  // 控制条自动隐藏
  let hideControlsTimer: ReturnType<typeof setTimeout> | null = null

  const scheduleHideControls = (delay = 2000): void => {
    if (hideControlsTimer) clearTimeout(hideControlsTimer)
    hideControlsTimer = setTimeout(() => {
      if (store.isDragging || store.showSettingsMenu || store.showQualityMenu || store.showPlaybackRateMenu) {
        scheduleHideControls(1500)
        return
      }
      store.setControlsVisible(false)
    }, delay)
  }

  // 事件处理函数
  const handleVideoPlay = (): void => {
    store.setNetworkFirstInteraction(false)
    store.setPlaying(true)
    store.setHasStartedPlayback(true)

    if (!isHlsStream.value && videoCore.value?.audioElement) {
      videoCore.value.audioElement.play().catch(err => {
        console.warn('Failed to sync audio play:', err)
      })
    }

    emit('play')
    scheduleHideControls(2000)
  }

  const handleVideoPause = (): void => {
    if (!store.seekingVideo) {
      store.setPlaying(false)
    }

    if (!isHlsStream.value && videoCore.value?.audioElement) {
      videoCore.value.audioElement.pause()
    }

    emit('pause')
    store.setControlsVisible(true)
  }

  // 音画同步纠偏
  const syncAvIfNeeded = (): void => {
    if (isHlsStream.value) return
    const v = videoCore.value?.videoElement
    const a = videoCore.value?.audioElement
    if (!v || !a) return
    if (store.seekingVideo || store.seekingAudio || store.isDragging) return
    const drift = a.currentTime - v.currentTime
    if (Math.abs(drift) > 0.1) {
      try { 
        a.currentTime = v.currentTime 
      } catch (e) {
        // Ignore sync errors
      }
    }
  }

  const handleVideoTimeupdate = (): void => {
    if (videoCore.value?.videoElement) {
      const currentTime = videoCore.value.videoElement.currentTime
      store.setCurrentTime(currentTime)

      if (videoCore.value.videoElement.duration &&
          videoCore.value.videoElement.duration !== Infinity) {
        store.setDuration(videoCore.value.videoElement.duration)
      }

      syncAvIfNeeded()
      savePlaybackProgress(currentTime)
      emit('timeupdate', currentTime)
    }
  }

  const handleVideoError = (error: any): void => {
    const errorInfo = handleError(error, {
      videoId: props.video?.id,
      isHlsStream: isHlsStream.value,
      reconnectAttempts: store.reconnectAttempts
    })

    store.setLoading(false)
    emit('error', { type: 'video', error, errorInfo })
  }

  const handleVideoLayerClick = (): void => {
    if (store.seekingState.active || store.volumeState.adjusting) {
      store.updateSeekingState({ active: false })
      store.updateVolumeState({ adjusting: false, showIndicator: false })
      return
    }

    if (!videoCore.value?.videoElement) return

    if (store.playing) {
      videoCore.value.videoElement.pause()
      if (videoCore.value.audioElement) {
        videoCore.value.audioElement.pause()
      }
    } else {
      if (store.networkFirstInteraction) {
        store.setNetworkFirstInteraction(false)
      }

      videoCore.value.videoElement.play().then(() => {
        if (videoCore.value?.audioElement) {
          videoCore.value.audioElement.play().catch(err => {
            console.error('Failed to play audio:', err)
          })
        }
      }).catch(err => {
        console.error('Failed to play video:', err)
      })
    }

    store.setShowPlayIndicator(true)
    setTimeout(() => store.setShowPlayIndicator(false), 500)
  }

  // 设置视频时间
  const setVideoTime = (time: number): void => {
    if (!videoCore.value?.videoElement) return
    const v = videoCore.value.videoElement
    v.currentTime = time
    const a = videoCore.value?.audioElement
    if (a) a.currentTime = time
    store.setCurrentTime(time)
  }

  // 进度保存逻辑
  let lastSavedTime = 0
  let saveProgressTimer: ReturnType<typeof setTimeout> | null = null

  const isVideoNearEnd = (lastPosition: number, duration: number): boolean => {
    if (!duration || duration <= 0 || !lastPosition || lastPosition <= 0) return false
    const progressPercent = (lastPosition / duration) * 100
    const remainingTime = duration - lastPosition
    if (duration < 300) return progressPercent >= 85
    if (duration < 1800) return progressPercent >= 90 || remainingTime < 120
    return progressPercent >= 95 || remainingTime < 180
  }

  const savePlaybackProgress = (currentTime: number): void => {
    if (saveProgressTimer) clearTimeout(saveProgressTimer)

    if (Math.abs(currentTime - lastSavedTime) >= 5) {
      saveProgressTimer = setTimeout(async () => {
        try {
          if (!props.video?.id) return

          updateLocalHistory(props.video.id, {
            last_position: currentTime,
            duration: store.duration,
            progress: (currentTime / store.duration) * 100,
            lastWatched: Date.now()
          })

          const shouldSendReport =
            Math.random() < 0.05 ||
            (currentTime - lastSavedTime) >= 30 ||
            isVideoNearEnd(currentTime, store.duration)

          if (shouldSendReport) {
            await sendReport(props.video.id, currentTime, {
              includeMetadata: false,
              retryOnFailure: false
            })
          }

          lastSavedTime = currentTime
        } catch (error) {
          console.warn('Failed to save progress:', error)
        }
      }, 2000)
    }
  }

  // 错误处理
  const handleRetry = (): void => {
    const success = manualRetry(() => {
      store.resetReconnectAttempts()
      if (videoCore.value?.videoElement) {
        videoCore.value.videoElement.load()
        videoCore.value.videoElement.play().catch(handleVideoError)
      }
    })
    if (!success) console.warn('Retry failed or not allowed')
  }

  const reportErrorToSupport = async (): Promise<void> => {
    try {
      await reportError({
        videoId: props.video?.id,
        videoUrl: props.video?.stream_video_url,
        userAction: 'manual_report',
        additionalContext: {
          playerState: {
            currentTime: store.currentTime,
            duration: store.duration,
            volume: store.volume,
            playbackRate: store.playbackRate
          }
        }
      })
      console.log('错误报告已发送')
    } catch (error) {
      console.error('Failed to report error:', error)
    }
  }

  const dismissError = (): void => clearError()

  // Pointer 事件
  const onPointerEnter = (): void => {
    store.setControlsVisible(true)
    scheduleHideControls(2000)
  }

  const onPointerLeave = (): void => scheduleHideControls(1500)

  const onPointerMove = (): void => {
    store.setControlsVisible(true)
    scheduleHideControls(2000)
  }

  // 自动播放逻辑
  const attemptAutoplay = async (): Promise<void> => {
    if (!videoCore.value?.videoElement) return
    if (!store.autoplay) return
    if (store.playing) return

    const wasFirstInteraction = store.networkFirstInteraction
    const originalMuted = store.muted

    try {
      store.setNetworkFirstInteraction(false)
      await videoCore.value.videoElement.play()

      if (!isHlsStream.value && videoCore.value.audioElement) {
        try {
          await videoCore.value.audioElement.play()
        } catch (audioError) {
          console.warn('Audio autoplay failed:', audioError)
        }
      }
    } catch (error) {
      console.warn('Video autoplay failed:', error)
      if (wasFirstInteraction && !originalMuted) {
        try {
          store.setMuted(true)
          await videoCore.value.videoElement.play()

          if (!isHlsStream.value && videoCore.value.audioElement) {
            try {
              await videoCore.value.audioElement.play()
            } catch (audioError) {
              console.warn('Muted audio autoplay failed:', audioError)
            }
          }

          setTimeout(() => store.setMuted(originalMuted), 1000)
        } catch (mutedError) {
          console.warn('Muted autoplay also failed:', mutedError)
          store.setMuted(originalMuted)
        }
      }
    }
  }

  // 监听自动播放条件
  watch([isCanplay, () => store.autoplay], ([canPlay, autoplay]) => {
    if (canPlay && autoplay && !store.playing) {
      setTimeout(() => attemptAutoplay(), 100)
    }
  }, { immediate: true })

  // 非 HLS 的加载速度探测
  let probeTimer: ReturnType<typeof setInterval> | null = null
  let probeAbort: AbortController | null = null
  let probeInFlight = false

  const runThroughputProbe = async (): Promise<void> => {
    if (probeInFlight) return
    const url = props.video?.stream_video_url
    if (!url) return
    if ((navigator as any)?.connection?.saveData) return

    probeInFlight = true
    const controller = new AbortController()
    probeAbort = controller
    const timeoutId = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS)

    try {
      const t0 = performance.now()
      const resp = await fetch(url, {
        method: 'GET',
        headers: { Range: `bytes=0-${PROBE_CHUNK_BYTES - 1}` },
        cache: 'no-store',
        mode: 'cors',
        credentials: 'omit',
        signal: controller.signal
      })

      if (!(resp.ok || resp.status === 206 || resp.status === 200)) return
      if (!resp.body) return

      const reader = resp.body.getReader()
      let loaded = 0
      while (loaded < PROBE_CHUNK_BYTES) {
        const { done, value } = await reader.read()
        if (done) break
        if (value && value.length) loaded += value.length
      }

      try { 
        controller.abort() 
      } catch (e) {
        // Ignore abort errors
      }

      const durationSec = Math.max(0.001, (performance.now() - t0) / 1000)
      if (loaded > 0 && durationSec > 0) {
        updateBandwidth(loaded, durationSec)
      }
    } catch (e) {
      // Ignore probe errors
    } finally {
      clearTimeout(timeoutId)
      probeInFlight = false
      probeAbort = null
    }
  }

  const startProbeMonitor = (): void => {
    if (probeTimer) return
    runThroughputProbe()
    probeTimer = setInterval(() => {
      if (store.loading && !isHlsStream.value) runThroughputProbe()
    }, PROBE_INTERVAL_MS)
  }

  const stopProbeMonitor = (): void => {
    if (probeTimer) {
      clearInterval(probeTimer)
      probeTimer = null
    }
    if (probeAbort) {
      try { 
        probeAbort.abort() 
      } catch (e) {
        // Ignore abort errors
      }
      probeAbort = null
    }
    probeInFlight = false
  }

  watch(() => store.loading, (loading) => {
    if (!isHlsStream.value) {
      if (loading) startProbeMonitor()
      else stopProbeMonitor()
    }
  })

  // 加载用户配置
  const loadUserConfig = async (): Promise<void> => {
    try {
      const response = await axios.get('/api/users/me/config')
      if (response.data.code === 0) {
        const config = response.data.data

        if (config.autoplay !== undefined) {
          store.setAutoplay(config.autoplay)
        } else {
          store.setAutoplay(true)
          saveUserConfig({ autoplay: true })
        }

        if (config.autoplayNext !== undefined) {
          store.setAutoplayNext(config.autoplayNext)
        } else {
          store.setAutoplayNext(true)
          saveUserConfig({ autoplayNext: true })
        }

        if (config.loop !== undefined) {
          store.setLoop(config.loop)
        }
      } else {
        store.setAutoplay(true)
        store.setAutoplayNext(true)
        saveUserConfig({ autoplay: true, autoplayNext: true })
      }
    } catch (error) {
      console.warn('Failed to load user config:', error)
      store.setAutoplay(true)
      store.setAutoplayNext(true)
    }
  }

  const saveUserConfig = async (settings: Record<string, any>): Promise<void> => {
    try {
      await axios.put('/api/users/me/config', { settings, merge: true })
    } catch (error) {
      console.warn('Failed to save user config:', error)
    }
  }

  // 监听设置变化并保存
  watch(() => store.autoplay, (newValue) => saveUserConfig({ autoplay: newValue }))
  watch(() => store.autoplayNext, (newValue) => saveUserConfig({ autoplayNext: newValue }))
  watch(() => store.loop, (newValue) => saveUserConfig({ loop: newValue }))

  onMounted(async () => {
    await loadUserConfig()

    try {
      updateFullscreenState()
      fullscreenEventNames.forEach(evt => 
        document.addEventListener(evt, updateFullscreenState)
      )
    } catch (e) {
      // Ignore event listener errors
    }

    console.log('[useVideoPlayer] onMounted, video ready with URL:', {
      hasStreamUrl: !!props.video?.stream_video_url,
      hasMpdUrl: !!props.video?.mpd_url,
      videoId: props.video?.id
    })

    // 开发调试工具
    if (typeof window !== 'undefined') {
      (window as any).debugVideoPlayer = () => {
        console.log('Video Player Debug Info:', {
          store: {
            playing: store.playing,
            muted: store.muted,
            volume: store.volume,
            autoplay: store.autoplay,
            canPlayVideo: store.canPlayVideo,
            canPlayAudio: store.canPlayAudio
          },
          elements: {
            hasVideoElement: !!videoCore.value?.videoElement,
            hasAudioElement: !!videoCore.value?.audioElement
          }
        })
      }
    }
  })

  // 监听视频变化
  watch(() => props.video?.id, (newId, oldId) => {
    if (newId && newId !== oldId) {
      store.resetForNewVideo()
    }

    if (newId && newId !== oldId && store.autoplay) {
      setTimeout(() => {
        if (isCanplay.value) attemptAutoplay()
      }, 200)
    }
  })

  onUnmounted(() => {
    if (saveProgressTimer) clearTimeout(saveProgressTimer)
    if (hideControlsTimer) clearTimeout(hideControlsTimer)
    stopProbeMonitor()
    try {
      fullscreenEventNames.forEach(evt => 
        document.removeEventListener(evt, updateFullscreenState)
      )
    } catch (e) {
      // Ignore event listener errors
    }
  })

  return {
    // Store
    store,

    // 性能状态
    performanceState,
    errorState,

    // 引用
    videoCore,

    // 计算属性
    isHlsStream,
    isDashStream,
    hasAudioStream,
    isCanplay,
    volumeIcon,
    fullscreenIcon,
    progress,
    supportsPiP,
    loadingStatusText,

    // 方法
    updateBandwidth,
    formatNetworkSpeed,
    handleVideoPlay,
    handleVideoPause,
    handleVideoTimeupdate,
    handleVideoError,
    handleVideoLayerClick,
    setVideoTime,
    getErrorInfo,
    handleRetry,
    reportErrorToSupport,
    dismissError,
    onPointerEnter,
    onPointerLeave,
    onPointerMove
  }
}
