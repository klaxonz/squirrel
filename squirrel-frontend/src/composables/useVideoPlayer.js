import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import useVideoHistory from './useVideoHistory'
import useVideoErrorHandler from './useVideoErrorHandler'
import usePerformanceMonitor from './usePerformanceMonitor'
import { usePlayerStore } from '../stores/playerStore'
import axios from '../utils/axios'

export default function useVideoPlayer(props, emit) {
  // DOM 引用
  const videoCore = ref(null)

  // 使用 Pinia store - 直接使用，不再代理
  const store = usePlayerStore()

  // 性能监控状态
  const performanceState = reactive({
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
    performanceState: perfState,
    updateBandwidth
  } = usePerformanceMonitor({
    hlsRef: null,
    videoRef: () => videoCore.value?.videoElement,
    externalPerformanceState: performanceState
  })

  // 计算属性
  const isHlsStream = computed(() =>
    !!props.video?.stream_video_url && props.video.stream_video_url.includes('.m3u8')
  )
  const isDashStream = computed(() =>
    !!props.video?.mpd_url || (!!props.video?.stream_video_url && props.video.stream_video_url.endsWith('.mpd'))
  )

  const hasAudioStream = computed(() => !!props.video?.stream_audio_url)

  const isCanplay = computed(() => {
    if (!hasAudioStream.value) {
      return store.canPlayVideo
    }
    return store.canPlayVideo && (isHlsStream.value || store.canPlayAudio)
  })

  // 直接使用 store 的计算属性
  const volumeIcon = computed(() => store.volumeIcon)
  const fullscreenIcon = computed(() => store.fullscreenIcon)
  const progress = computed(() => store.progress)
  const loadingStatusText = computed(() => store.loadingStatusText)

  const supportsPiP = computed(() =>
    !!(document.pictureInPictureEnabled && videoCore.value?.videoElement)
  )

  // 同步全屏状态
  const getPlayerContainer = () => {
    const videoEl = videoCore.value?.videoElement
    if (!videoEl) return null
    let container = videoEl.parentElement
    while (container && !container.classList?.contains('video-player-container')) {
      container = container.parentElement
    }
    return container || null
  }

  const getDocFullscreenElement = () => {
    return (
      document.fullscreenElement ||
      document.webkitFullscreenElement ||
      document.mozFullScreenElement ||
      document.msFullscreenElement ||
      null
    )
  }

  const updateFullscreenState = () => {
    try {
      const container = getPlayerContainer()
      const fsEl = getDocFullscreenElement()
      const isFs = !!(container && fsEl === container)
      if (store.fullscreen !== isFs) {
        store.setFullscreen(isFs)
        try { emit && emit('fullscreenChange', isFs) } catch (e) {}
      }
    } catch (e) {}
  }

  const fullscreenEventNames = ['fullscreenchange', 'webkitfullscreenchange', 'mozfullscreenchange', 'MSFullscreenChange']

  // 格式化网络速度
  const formatNetworkSpeed = (bps) => {
    if (!bps || bps <= 0) return ''
    const bytesPerSecond = bps / 8
    const mBps = bytesPerSecond / 1024 / 1024
    const kBps = bytesPerSecond / 1024
    if (mBps >= 1) return `${mBps.toFixed(1)} MB/s`
    return `${Math.round(kBps)} KB/s`
  }

  // 事件处理函数
  const handleVideoPlay = () => {
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

  const handleVideoPause = () => {
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
  const syncAvIfNeeded = () => {
    if (isHlsStream.value) return
    const v = videoCore.value?.videoElement
    const a = videoCore.value?.audioElement
    if (!v || !a) return
    if (store.seekingVideo || store.seekingAudio || store.isDragging) return
    const drift = a.currentTime - v.currentTime
    if (Math.abs(drift) > 0.1) {
      try { a.currentTime = v.currentTime } catch (e) {}
    }
  }

  const handleVideoTimeupdate = () => {
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

  const handleVideoError = (error) => {
    const errorInfo = handleError(error, {
      videoId: props.video?.id,
      isHlsStream: isHlsStream.value,
      reconnectAttempts: store.reconnectAttempts
    })

    store.setLoading(false)
    emit('error', { type: 'video', error, errorInfo })
  }

  const handleVideoLayerClick = () => {
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
        if (videoCore.value.audioElement) {
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
  const setVideoTime = (time) => {
    if (!videoCore.value?.videoElement) return
    const v = videoCore.value.videoElement
    v.currentTime = time
    const a = videoCore.value?.audioElement
    if (a) a.currentTime = time
    store.setCurrentTime(time)
  }

  // 进度保存逻辑
  let lastSavedTime = 0
  let saveProgressTimer = null

  const savePlaybackProgress = (currentTime) => {
    if (saveProgressTimer) clearTimeout(saveProgressTimer)

    if (Math.abs(currentTime - lastSavedTime) >= 5) {
      saveProgressTimer = setTimeout(async () => {
        try {
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

  const isVideoNearEnd = (lastPosition, duration) => {
    if (!duration || duration <= 0 || !lastPosition || lastPosition <= 0) return false
    const progress = (lastPosition / duration) * 100
    const remainingTime = duration - lastPosition
    if (duration < 300) return progress >= 85
    if (duration < 1800) return progress >= 90 || remainingTime < 120
    return progress >= 95 || remainingTime < 180
  }

  // 错误处理
  const handleRetry = () => {
    const success = manualRetry(() => {
      store.resetReconnectAttempts()
      if (videoCore.value) {
        videoCore.value.videoElement.load()
        videoCore.value.videoElement.play().catch(handleVideoError)
      }
    })
    if (!success) console.warn('Retry failed or not allowed')
  }

  const reportErrorToSupport = async () => {
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

  const dismissError = () => clearError()

  // Pointer 事件与自动隐藏控制条
  let hideControlsTimer = null

  const scheduleHideControls = (delay = 2000) => {
    if (hideControlsTimer) clearTimeout(hideControlsTimer)
    hideControlsTimer = setTimeout(() => {
      if (store.isDragging || store.showSettingsMenu || store.showQualityMenu || store.showPlaybackRateMenu) {
        scheduleHideControls(1500)
        return
      }
      store.setControlsVisible(false)
    }, delay)
  }

  const onPointerEnter = () => {
    store.setControlsVisible(true)
    scheduleHideControls(2000)
  }

  const onPointerLeave = () => scheduleHideControls(1500)

  const onPointerMove = () => {
    store.setControlsVisible(true)
    scheduleHideControls(2000)
  }

  // 自动播放逻辑
  const attemptAutoplay = async () => {
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
  let probeTimer = null
  let probeAbort = null
  let probeInFlight = false
  const PROBE_INTERVAL_MS = 1000
  const PROBE_CHUNK_BYTES = 128 * 1024
  const PROBE_TIMEOUT_MS = 4000

  const runThroughputProbe = async () => {
    if (probeInFlight) return
    const url = props.video?.stream_video_url
    if (!url) return
    if (navigator?.connection?.saveData) return

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

      try { controller.abort() } catch (e) {}

      const durationSec = Math.max(0.001, (performance.now() - t0) / 1000)
      if (loaded > 0 && durationSec > 0) {
        updateBandwidth(loaded, durationSec)
      }
    } catch (e) {
    } finally {
      clearTimeout(timeoutId)
      probeInFlight = false
      probeAbort = null
    }
  }

  const startProbeMonitor = () => {
    if (probeTimer) return
    runThroughputProbe()
    probeTimer = setInterval(() => {
      if (store.loading && !isHlsStream.value) runThroughputProbe()
    }, PROBE_INTERVAL_MS)
  }

  const stopProbeMonitor = () => {
    if (probeTimer) {
      clearInterval(probeTimer)
      probeTimer = null
    }
    if (probeAbort) {
      try { probeAbort.abort() } catch (e) {}
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
  const loadUserConfig = async () => {
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

  const saveUserConfig = async (settings) => {
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
      fullscreenEventNames.forEach(evt => document.addEventListener(evt, updateFullscreenState))
    } catch (e) {}

    console.log('[useVideoPlayer] onMounted, video ready with URL:', {
      hasStreamUrl: !!props.video?.stream_video_url,
      hasMpdUrl: !!props.video?.mpd_url,
      videoId: props.video?.id
    })

    if (typeof window !== 'undefined') {
      window.debugVideoPlayer = () => {
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
      fullscreenEventNames.forEach(evt => document.removeEventListener(evt, updateFullscreenState))
    } catch (e) {}
  })

  return {
    // Store - 直接暴露给组件使用
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
