import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import useVideoOperations from './useVideoOperations'
import useVideoHistory from './useVideoHistory'
import useVideoErrorHandler from './useVideoErrorHandler'
import useVideoPreload from './useVideoPreload'
import useHlsPlayer from './useHlsPlayer'
import usePerformanceMonitor from './usePerformanceMonitor'
import { formatTime } from '../utils/dateFormat'
import axios from '../utils/axios'

export default function useVideoPlayer(props, emit) {
  // DOM 引用
  const videoCore = ref(null)
  
  // 统一状态管理
  const playerState = reactive({
    media: {
      playing: false,
      canPlay: { video: false, audio: false },
      seeking: { video: false, audio: false },
      loading: false,
      loadingStage: 'idle',
      volume: 100,
      muted: false,
      currentTime: 0,
      duration: 0,
      bufferedProgress: 0,
      firstInteraction: true,
      playbackRate: 1,
      subtitlesEnabled: false,
      pictureInPicture: false,
      currentQuality: 'auto',
      currentSubtitle: null,
      autoplay: false,
      loop: false
    },
    ui: {
      controlsVisible: true,
      fullscreen: false,
      theaterMode: false,
      showPlayIndicator: false,
      isDragging: false,
      errorMessage: null,
      showPlaybackRateMenu: false,
      showQualityMenu: false,
      showSettingsMenu: false,
      showKeyboardHelp: false,
      showKeyboardFeedback: false,
      keyboardFeedback: '',
      seeking: {
        active: false,
        startX: 0,
        currentX: 0,
        distance: 0,
        direction: null,
        seekTime: 0,
        wasPlaying: false
      },
      volume: {
        adjusting: false,
        startY: 0,
        startVolume: 0,
        showIndicator: false
      }
    },
    network: {
      reconnectAttempts: 0,
      firstInteraction: true
    }
  })

  // 性能监控状态
  const performanceState = reactive({
    bandwidth: { samples: [], average: 0, current: 0 },
    memory: { used: 0, peak: 0, lastCleanup: 0 },
    loading: { startTime: 0, duration: 0, bytesLoaded: 0 }
  })

  // 组合函数
  const { playVideo } = useVideoOperations()
  
  const {
    sendReport,
    getLocalHistory,
    updateLocalHistory,
    setupNetworkListeners,
    startPeriodicSync
  } = useVideoHistory()

  const {
    errorState,
    handleError,
    manualRetry,
    clearError,
    getErrorInfo,
    reportError
  } = useVideoErrorHandler()

  const {
    detectNetworkCondition,
    getOptimizedHlsConfig,
    preloadVideo,
    setupNetworkListener
  } = useVideoPreload()

  const {
    performanceState: perfState,
    monitorNetworkSpeed,
    monitorPerformance,
    updateBandwidth
  } = usePerformanceMonitor({ 
    hlsRef: null, 
    videoRef: () => videoCore.value?.videoElement, 
    externalPerformanceState: performanceState 
  })

  // 计算属性
  const isHlsStream = computed(() => 
    props.video?.stream_video_url?.includes('.m3u8')
  )

  const hasAudioStream = computed(() => {
    return !!props.video?.stream_audio_url
  })

  const isCanplay = computed(() => {
    if (!hasAudioStream.value) {
      return playerState.media.canPlay.video
    }
    return playerState.media.canPlay.video && 
      (isHlsStream.value || playerState.media.canPlay.audio)
  })

  const volumeIcon = computed(() => {
    if (playerState.media.muted || playerState.media.volume === 0) 
      return 'material-symbols:volume-off'
    if (playerState.media.volume < 50) 
      return 'material-symbols:volume-down'
    return 'material-symbols:volume-up'
  })

  const fullscreenIcon = computed(() => 
    playerState.ui.fullscreen ? 'material-symbols:fullscreen-exit' : 'material-symbols:fullscreen'
  )

  const progress = computed(() => {
    return (playerState.media.currentTime / playerState.media.duration) * 100 || 0
  })

  const supportsPiP = computed(() =>
    !!(document.pictureInPictureEnabled && videoCore.value?.videoElement)
  )

  const loadingStatusText = computed(() => {
    switch (playerState.media.loadingStage) {
      case 'fetching': return '获取视频链接中...'
      case 'buffering': return '缓冲中...'
      case 'ready': return '准备就绪'
      default: return '加载中...'
    }
  })

  // 格式化网络速度（输入为 bps -> 显示为 MB/s 或 KB/s）
  const formatNetworkSpeed = (bps) => {
    if (!bps || bps <= 0) return ''

    const bytesPerSecond = bps / 8
    const mBps = bytesPerSecond / 1024 / 1024
    const kBps = bytesPerSecond / 1024

    if (mBps >= 1) {
      return `${mBps.toFixed(1)} MB/s`
    }
    return `${Math.round(kBps)} KB/s`
  }

  // 事件处理函数
  const handleVideoPlay = () => {
    playerState.network.firstInteraction = false
    // 视频实际开始播放时，无条件更新状态
    playerState.media.playing = true

    // 确保音频也在播放（非HLS情况下）
    if (!isHlsStream.value && videoCore.value?.audioElement) {
      videoCore.value.audioElement.play().catch(err => {
        console.warn('Failed to sync audio play:', err)
      })
    }

    emit('play')
  }

  const handleVideoPause = () => {
    // 视频实际暂停时，无条件更新状态（除非正在seeking）
    if (!playerState.media.seeking.video) {
      playerState.media.playing = false
    }

    // 确保音频也暂停（非HLS情况下）
    if (!isHlsStream.value && videoCore.value?.audioElement) {
      videoCore.value.audioElement.pause()
    }

    emit('pause')
  }

  // 音画同步纠偏（仅非HLS且存在独立音频时）
  const syncAvIfNeeded = () => {
    if (isHlsStream.value) return
    const v = videoCore.value?.videoElement
    const a = videoCore.value?.audioElement
    if (!v || !a) return
    if (playerState.media.seeking.video || playerState.media.seeking.audio || playerState.ui.isDragging) return
    const drift = a.currentTime - v.currentTime
    // 超过100ms则硬同步
    if (Math.abs(drift) > 0.1) {
      try { a.currentTime = v.currentTime } catch (e) {}
    }
  }

  const handleVideoTimeupdate = () => {
    if (videoCore.value?.videoElement) {
      const currentTime = videoCore.value.videoElement.currentTime
      playerState.media.currentTime = currentTime

      if (videoCore.value.videoElement.duration &&
          videoCore.value.videoElement.duration !== Infinity) {
        playerState.media.duration = videoCore.value.videoElement.duration
      }

      // 在正常播放时做一次轻量纠偏
      syncAvIfNeeded()

      savePlaybackProgress(currentTime)
      emit('timeupdate', currentTime)
    }
  }

  const handleVideoError = (error) => {
    console.error('Video error:', error)
    
    const errorInfo = handleError(error, {
      videoId: props.video?.id,
      isHlsStream: isHlsStream.value,
      reconnectAttempts: playerState.network.reconnectAttempts
    })
    
    playerState.media.loading = false
    emit('error', { type: 'video', error, errorInfo })
  }

  const handleVideoLayerClick = () => {
    // 重置可能卡住的状态
    if (playerState.ui.seeking.active || playerState.ui.volume.adjusting) {
      playerState.ui.seeking.active = false
      playerState.ui.volume.adjusting = false
      playerState.ui.volume.showIndicator = false
      return
    }

    // 直接控制视频播放
    if (!videoCore.value?.videoElement) return

    if (playerState.media.playing) {
      videoCore.value.videoElement.pause()
      if (videoCore.value.audioElement) {
        videoCore.value.audioElement.pause()
      }
    } else {
      if (playerState.network.firstInteraction) {
        playerState.network.firstInteraction = false
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

    playerState.ui.showPlayIndicator = true
    setTimeout(() => {
      playerState.ui.showPlayIndicator = false
    }, 500)
  }

  // 设置视频时间（包含A/V同步）
  const setVideoTime = (time) => {
    if (!videoCore.value?.videoElement) return
    const v = videoCore.value.videoElement
    v.currentTime = time
    const a = videoCore.value?.audioElement
    if (a) {
      a.currentTime = time
    }
    playerState.media.currentTime = time
  }

  // 进度保存逻辑
  let lastSavedTime = 0
  let saveProgressTimer = null

  const savePlaybackProgress = (currentTime) => {
    if (saveProgressTimer) {
      clearTimeout(saveProgressTimer)
    }

    if (Math.abs(currentTime - lastSavedTime) >= 5) {
      saveProgressTimer = setTimeout(async () => {
        try {
          updateLocalHistory(props.video.id, {
            last_position: currentTime,
            duration: playerState.media.duration,
            progress: (currentTime / playerState.media.duration) * 100,
            lastWatched: Date.now()
          })

          const shouldSendReport =
            Math.random() < 0.05 ||
            (currentTime - lastSavedTime) >= 30 ||
            isVideoNearEnd(currentTime, playerState.media.duration)

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
    if (!duration || duration <= 0 || !lastPosition || lastPosition <= 0) {
      return false
    }

    const progress = (lastPosition / duration) * 100
    const remainingTime = duration - lastPosition

    if (duration < 300) {
      return progress >= 85
    }

    if (duration < 1800) {
      return progress >= 90 || remainingTime < 120
    }

    return progress >= 95 || remainingTime < 180
  }

  // 错误处理
  const handleRetry = () => {
    const success = manualRetry(() => {
      playerState.network.reconnectAttempts = 0
      // 重新初始化播放器
      if (videoCore.value) {
        videoCore.value.videoElement.load()
        videoCore.value.videoElement.play().catch(handleVideoError)
      }
    })

    if (!success) {
      console.warn('Retry failed or not allowed')
    }
  }

  const reportErrorToSupport = async () => {
    try {
      await reportError({
        videoId: props.video?.id,
        videoUrl: props.video?.stream_video_url,
        userAction: 'manual_report',
        additionalContext: {
          playerState: {
            currentTime: playerState.media.currentTime,
            duration: playerState.media.duration,
            volume: playerState.media.volume,
            playbackRate: playerState.media.playbackRate
          }
        }
      })
      console.log('错误报告已发送')
    } catch (error) {
      console.error('Failed to report error:', error)
    }
  }

  const dismissError = () => {
    clearError()
  }

  // Pointer 事件处理
  let hideControlsTimer = null

  const onPointerEnter = () => {
    playerState.ui.controlsVisible = true
    if (hideControlsTimer) {
      clearTimeout(hideControlsTimer)
      hideControlsTimer = null
    }
  }

  const onPointerLeave = () => {
    hideControlsTimer = setTimeout(() => {
      playerState.ui.controlsVisible = false
    }, 2000)
  }

  const onPointerMove = () => {
    playerState.ui.controlsVisible = true

    if (hideControlsTimer) {
      clearTimeout(hideControlsTimer)
      hideControlsTimer = null
    }

    hideControlsTimer = setTimeout(() => {
      playerState.ui.controlsVisible = false
    }, 2000)
  }

  // 自动播放逻辑
  const attemptAutoplay = async () => {
    if (!videoCore.value?.videoElement) {
      console.log('No video element for autoplay')
      return
    }

    if (!playerState.media.autoplay) {
      console.log('Autoplay disabled')
      return
    }

    if (playerState.media.playing) {
      console.log('Already playing')
      return
    }

    console.log('Attempting autoplay...', {
      isHlsStream: isHlsStream.value,
      hasAudioElement: !!videoCore.value.audioElement,
      videoMuted: videoCore.value.videoElement.muted,
      audioMuted: videoCore.value.audioElement?.muted,
      playerMuted: playerState.media.muted,
      volume: playerState.media.volume
    })

    const wasFirstInteraction = playerState.network.firstInteraction
    const originalMuted = playerState.media.muted

    try {
      // 如果是首次交互且未静音，先尝试正常播放
      playerState.network.firstInteraction = false

      await videoCore.value.videoElement.play()
      console.log('Video play successful')

      if (!isHlsStream.value && videoCore.value.audioElement) {
        try {
          await videoCore.value.audioElement.play()
          console.log('Audio play successful')
        } catch (audioError) {
          console.warn('Audio autoplay failed:', audioError)
        }
      }

    } catch (error) {
      console.warn('Video autoplay failed:', error)
      // 如果正常播放失败且是首次交互，尝试静音播放
      if (wasFirstInteraction && !originalMuted) {
        try {
          console.log('Trying muted autoplay')
          playerState.media.muted = true

          await videoCore.value.videoElement.play()
          console.log('Muted video play successful')

          if (!isHlsStream.value && videoCore.value.audioElement) {
            try {
              await videoCore.value.audioElement.play()
              console.log('Muted audio play successful')
            } catch (audioError) {
              console.warn('Muted audio autoplay failed:', audioError)
            }
          }

          // 播放成功后，延迟恢复音量
          setTimeout(() => {
            console.log('Restoring original muted state:', originalMuted)
            playerState.media.muted = originalMuted
          }, 1000)

        } catch (mutedError) {
          console.warn('Muted autoplay also failed:', mutedError)
          playerState.media.muted = originalMuted
        }
      }
    }
  }

  // 监听自动播放条件
  watch([isCanplay, () => playerState.media.autoplay], ([canPlay, autoplay]) => {
    if (canPlay && autoplay && !playerState.media.playing) {
      // 延迟一小段时间确保所有媒体元素都准备好
      setTimeout(() => {
        attemptAutoplay()
      }, 100)
    }
  }, { immediate: true })

  // 生命周期
  // 非 HLS 的加载速度（吞吐采样：小范围 Range 请求统计真实字节/耗时）
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

      // 尽快结束本次探测
      try { controller.abort() } catch (e) {}

      const durationSec = Math.max(0.001, (performance.now() - t0) / 1000)
      if (loaded > 0 && durationSec > 0) {
        updateBandwidth(loaded, durationSec)
      }
    } catch (e) {
      // 忽略单次失败，下一轮重试
    } finally {
      clearTimeout(timeoutId)
      probeInFlight = false
      probeAbort = null
    }
  }

  const startProbeMonitor = () => {
    if (probeTimer) return
    // 立即采样一次
    runThroughputProbe()
    probeTimer = setInterval(() => {
      if (playerState.media.loading && !isHlsStream.value) runThroughputProbe()
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

  watch(() => playerState.media.loading, (loading) => {
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

        // 设置自动播放，默认为true以提供更好的用户体验
        if (config.autoplay !== undefined) {
          playerState.media.autoplay = config.autoplay
        } else {
          playerState.media.autoplay = true
          // 保存默认设置到后端
          saveUserConfig({ autoplay: true })
        }

        if (config.loop !== undefined) {
          playerState.media.loop = config.loop
        }
      } else {
        // 如果获取配置失败，使用默认值
        playerState.media.autoplay = true
        saveUserConfig({ autoplay: true })
      }
    } catch (error) {
      console.warn('Failed to load user config:', error)
      // 如果加载失败，使用默认值
      playerState.media.autoplay = true
    }
  }

  // 保存用户配置
  const saveUserConfig = async (settings) => {
    try {
      await axios.put('/api/users/me/config', {
        settings,
        merge: true
      })
    } catch (error) {
      console.warn('Failed to save user config:', error)
    }
  }

  // 监听自动播放设置变化并保存
  watch(() => playerState.media.autoplay, (newValue) => {
    saveUserConfig({ autoplay: newValue })
  })

  // 监听循环播放设置变化并保存
  watch(() => playerState.media.loop, (newValue) => {
    saveUserConfig({ loop: newValue })
  })

  onMounted(async () => {
    setupNetworkListener()
    await loadUserConfig()

    if (!props.video?.stream_video_url) {
      await playVideo(props.video)
    }

    // 调试函数
    if (typeof window !== 'undefined') {
      window.debugVideoPlayer = () => {
        console.log('Video Player Debug Info:', {
          playerState: {
            playing: playerState.media.playing,
            muted: playerState.media.muted,
            volume: playerState.media.volume,
            autoplay: playerState.media.autoplay,
            canPlay: playerState.media.canPlay
          },
          elements: {
            hasVideoElement: !!videoCore.value?.videoElement,
            hasAudioElement: !!videoCore.value?.audioElement,
            videoMuted: videoCore.value?.videoElement?.muted,
            audioMuted: videoCore.value?.audioElement?.muted,
            videoVolume: videoCore.value?.videoElement?.volume,
            audioVolume: videoCore.value?.audioElement?.volume,
            videoPaused: videoCore.value?.videoElement?.paused,
            audioPaused: videoCore.value?.audioElement?.paused
          },
          stream: {
            isHlsStream: isHlsStream.value,
            hasAudioStream: hasAudioStream.value,
            videoUrl: props.video?.stream_video_url,
            audioUrl: props.video?.stream_audio_url
          }
        })
      }
    }
  })

  // 监听视频变化，支持自动播放新视频
  watch(() => props.video?.id, (newId, oldId) => {
    if (newId && newId !== oldId && playerState.media.autoplay) {
      // 重置播放状态
      playerState.media.playing = false
      playerState.media.canPlay.video = false
      playerState.media.canPlay.audio = false

      // 等待新视频加载完成后尝试自动播放
      setTimeout(() => {
        if (isCanplay.value) {
          attemptAutoplay()
        }
      }, 200)
    }
  })

  onUnmounted(() => {
    if (saveProgressTimer) clearTimeout(saveProgressTimer)
    if (hideControlsTimer) clearTimeout(hideControlsTimer)
    stopProbeMonitor()
  })

  return {
    // 状态
    playerState,
    performanceState,
    errorState,
    
    // 引用
    videoCore,
    
    // 计算属性
    isHlsStream,
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
