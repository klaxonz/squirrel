import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import useVideoOperations from './useVideoOperations'
import useVideoHistory from './useVideoHistory'
import useVideoErrorHandler from './useVideoErrorHandler'
import useVideoPreload from './useVideoPreload'
import useHlsPlayer from './useHlsPlayer'
import usePerformanceMonitor from './usePerformanceMonitor'
import { formatTime } from '../utils/dateFormat'

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
      hoveringProgress: false,
      hoverPosition: 0,
      previewTime: 0,
      showPlayIndicator: false,
      isDragging: false,
      previewSeekTime: 0,
      errorMessage: null,
      showPlaybackRateMenu: false,
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
    if (playerState.ui.isDragging) {
      return (playerState.ui.previewSeekTime / playerState.media.duration) * 100 || 0
    }
    return (playerState.media.currentTime / playerState.media.duration) * 100 || 0
  })

  const supportsPiP = computed(() =>
    document.pictureInPictureEnabled && videoCore.value?.videoElement
  )

  const loadingStatusText = computed(() => {
    switch (playerState.media.loadingStage) {
      case 'fetching': return '获取视频链接中...'
      case 'buffering': return '缓冲中...'
      case 'ready': return '准备就绪'
      default: return '加载中...'
    }
  })

  // 格式化网络速度
  const formatNetworkSpeed = (bytesPerSecond) => {
    if (!bytesPerSecond || bytesPerSecond === 0) return '--'
    
    const mbps = (bytesPerSecond / 1024 / 1024).toFixed(1)
    const kbps = (bytesPerSecond / 1024).toFixed(0)
    
    if (mbps >= 1) {
      return `${mbps} MB/s`
    } else {
      return `${kbps} KB/s`
    }
  }

  // 事件处理函数
  const handleVideoPlay = () => {
    playerState.network.firstInteraction = false
    if (isCanplay.value) {
      playerState.media.playing = true
    }
    emit('play')
  }

  const handleVideoPause = () => {
    if (!playerState.media.seeking.video) {
      playerState.media.playing = false
    }
    emit('pause')
  }

  const handleVideoTimeupdate = () => {
    if (videoCore.value?.videoElement) {
      const currentTime = videoCore.value.videoElement.currentTime
      playerState.media.currentTime = currentTime
      
      if (videoCore.value.videoElement.duration && 
          videoCore.value.videoElement.duration !== Infinity) {
        playerState.media.duration = videoCore.value.videoElement.duration
      }
      
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
    if (playerState.ui.seeking.active || playerState.ui.volume.adjusting) {
      return
    }
    
    // 这里需要调用 togglePlay，但它在 useVideoControls 中定义
    // 可以通过事件或者回调来处理
    emit('toggle-play')
    
    playerState.ui.showPlayIndicator = true
    setTimeout(() => {
      playerState.ui.showPlayIndicator = false
    }, 500)
  }

  // 设置视频时间
  const setVideoTime = (time) => {
    if (!videoCore.value?.videoElement) return
    videoCore.value.videoElement.currentTime = time
    if (videoCore.value?.audioElement) {
      videoCore.value.audioElement.currentTime = time
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
      if (!playerState.ui.hoveringProgress) {
        playerState.ui.controlsVisible = false
      }
    }, 2000)
  }

  const onPointerMove = () => {
    playerState.ui.controlsVisible = true

    if (hideControlsTimer) {
      clearTimeout(hideControlsTimer)
      hideControlsTimer = null
    }

    hideControlsTimer = setTimeout(() => {
      if (!playerState.ui.hoveringProgress) {
        playerState.ui.controlsVisible = false
      }
    }, 2000)
  }

  // 生命周期
  onMounted(async () => {
    setupNetworkListener()
    
    if (!props.video?.stream_video_url) {
      await playVideo(props.video)
    }
  })

  onUnmounted(() => {
    if (saveProgressTimer) clearTimeout(saveProgressTimer)
    if (hideControlsTimer) clearTimeout(hideControlsTimer)
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
