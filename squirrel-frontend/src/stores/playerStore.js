import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const usePlayerStore = defineStore('player', () => {
  // ========== Media State ==========
  const playing = ref(false)
  const canPlayVideo = ref(false)
  const canPlayAudio = ref(false)
  const seekingVideo = ref(false)
  const seekingAudio = ref(false)
  const loading = ref(false)
  const loadingStage = ref('idle') // idle | fetching | buffering | ready
  const volume = ref(100)
  const muted = ref(false)
  const currentTime = ref(0)
  const duration = ref(0)
  const bufferedProgress = ref(0)
  const firstInteraction = ref(true)
  const playbackRate = ref(1)
  const subtitlesEnabled = ref(false)
  const pictureInPicture = ref(false)
  const hasStartedPlayback = ref(false)
  const currentQuality = ref(null)
  const currentSubtitle = ref(null)
  const autoplay = ref(false)
  const autoplayNext = ref(true)
  const loop = ref(false)

  // Subtitle settings
  const subtitleSettings = ref({
    fontSize: 'medium',
    color: 'white',
    bgOpacity: 0.4,
    position: 'bottom',
    shadow: true
  })

  // ========== UI State ==========
  const controlsVisible = ref(true)
  const fullscreen = ref(false)
  const theaterMode = ref(false)
  const showPlayIndicator = ref(false)
  const isDragging = ref(false)
  const errorMessage = ref(null)
  const showPlaybackRateMenu = ref(false)
  const showQualityMenu = ref(false)
  const showSettingsMenu = ref(false)
  const showSubtitlesMenu = ref(false)
  const showKeyboardHelp = ref(false)
  const showKeyboardFeedback = ref(false)
  const keyboardFeedback = ref('')

  // Seeking state
  const seekingState = ref({
    active: false,
    startX: 0,
    currentX: 0,
    distance: 0,
    direction: null,
    seekTime: 0,
    wasPlaying: false
  })

  // Volume adjustment state
  const volumeState = ref({
    adjusting: false,
    startY: 0,
    startVolume: 0,
    showIndicator: false
  })

  // ========== Network State ==========
  const reconnectAttempts = ref(0)
  const networkFirstInteraction = ref(true)

  // ========== Computed (Getters) ==========
  const canPlay = computed(() => ({
    video: canPlayVideo.value,
    audio: canPlayAudio.value
  }))

  const seeking = computed(() => ({
    video: seekingVideo.value,
    audio: seekingAudio.value
  }))

  const progress = computed(() => {
    return (currentTime.value / duration.value) * 100 || 0
  })

  const volumeIcon = computed(() => {
    if (muted.value || volume.value === 0) return 'material-symbols:volume-off'
    if (volume.value < 50) return 'material-symbols:volume-down'
    return 'material-symbols:volume-up'
  })

  const fullscreenIcon = computed(() =>
    fullscreen.value ? 'material-symbols:fullscreen-exit' : 'material-symbols:fullscreen'
  )

  const loadingStatusText = computed(() => {
    switch (loadingStage.value) {
      case 'fetching': return '获取视频链接中...'
      case 'buffering': return '缓冲中...'
      case 'ready': return '准备就绪'
      default: return '加载中...'
    }
  })

  // ========== Actions ==========
  // Media actions
  function setPlaying(value) {
    playing.value = value
  }

  function setCanPlay(type, value) {
    if (type === 'video') canPlayVideo.value = value
    else if (type === 'audio') canPlayAudio.value = value
  }

  function setSeeking(type, value) {
    if (type === 'video') seekingVideo.value = value
    else if (type === 'audio') seekingAudio.value = value
  }

  function setLoading(value, stage = null) {
    loading.value = value
    if (stage !== null) loadingStage.value = stage
  }

  function setVolume(value) {
    volume.value = Math.max(0, Math.min(100, value))
  }

  function setMuted(value) {
    muted.value = value
  }

  function toggleMute() {
    muted.value = !muted.value
  }

  function setCurrentTime(value) {
    currentTime.value = value
  }

  function setDuration(value) {
    duration.value = value
  }

  function setBufferedProgress(value) {
    bufferedProgress.value = value
  }

  function setPlaybackRate(value) {
    playbackRate.value = value
  }

  function setCurrentQuality(value) {
    currentQuality.value = value
  }

  function setSubtitlesEnabled(value) {
    subtitlesEnabled.value = value
  }

  function toggleSubtitles() {
    subtitlesEnabled.value = !subtitlesEnabled.value
  }

  function setCurrentSubtitle(value) {
    currentSubtitle.value = value
  }

  function updateSubtitleSettings(settings) {
    subtitleSettings.value = { ...subtitleSettings.value, ...settings }
  }

  function setAutoplay(value) {
    autoplay.value = value
  }

  function setAutoplayNext(value) {
    autoplayNext.value = value
  }

  function setLoop(value) {
    loop.value = value
  }

  function setPictureInPicture(value) {
    pictureInPicture.value = value
  }

  function setHasStartedPlayback(value) {
    hasStartedPlayback.value = value
  }

  // UI actions
  function setControlsVisible(value) {
    controlsVisible.value = value
  }

  function setFullscreen(value) {
    fullscreen.value = value
  }

  function toggleFullscreen() {
    fullscreen.value = !fullscreen.value
  }

  function setTheaterMode(value) {
    theaterMode.value = value
  }

  function toggleTheaterMode() {
    theaterMode.value = !theaterMode.value
  }

  function setShowPlayIndicator(value) {
    showPlayIndicator.value = value
  }

  function setIsDragging(value) {
    isDragging.value = value
  }

  function setShowMenu(menuName, value) {
    // 关闭所有菜单
    showPlaybackRateMenu.value = false
    showQualityMenu.value = false
    showSettingsMenu.value = false
    showSubtitlesMenu.value = false

    // 打开指定菜单
    switch (menuName) {
      case 'playbackRate':
        showPlaybackRateMenu.value = value
        break
      case 'quality':
        showQualityMenu.value = value
        break
      case 'settings':
        showSettingsMenu.value = value
        break
      case 'subtitles':
        showSubtitlesMenu.value = value
        break
    }
  }

  function closeAllMenus() {
    showPlaybackRateMenu.value = false
    showQualityMenu.value = false
    showSettingsMenu.value = false
    showSubtitlesMenu.value = false
  }

  function setShowKeyboardHelp(value) {
    showKeyboardHelp.value = value
  }

  function showKeyboardFeedbackMessage(message) {
    keyboardFeedback.value = message
    showKeyboardFeedback.value = true
    setTimeout(() => {
      showKeyboardFeedback.value = false
    }, 1000)
  }

  function updateSeekingState(updates) {
    seekingState.value = { ...seekingState.value, ...updates }
  }

  function resetSeekingState() {
    seekingState.value = {
      active: false,
      startX: 0,
      currentX: 0,
      distance: 0,
      direction: null,
      seekTime: 0,
      wasPlaying: false
    }
  }

  function updateVolumeState(updates) {
    volumeState.value = { ...volumeState.value, ...updates }
  }

  // Network actions
  function incrementReconnectAttempts() {
    reconnectAttempts.value++
  }

  function resetReconnectAttempts() {
    reconnectAttempts.value = 0
  }

  function setNetworkFirstInteraction(value) {
    networkFirstInteraction.value = value
  }

  // Reset all state (when switching videos)
  function resetForNewVideo() {
    // 媒体状态
    playing.value = false
    canPlayVideo.value = false
    canPlayAudio.value = false
    seekingVideo.value = false
    seekingAudio.value = false
    loading.value = true
    loadingStage.value = 'fetching'
    currentTime.value = 0
    duration.value = 0
    bufferedProgress.value = 0
    hasStartedPlayback.value = false
    pictureInPicture.value = false
    
    // 字幕状态
    currentSubtitle.value = null
    subtitlesEnabled.value = false
    
    // 网络状态
    reconnectAttempts.value = 0
    networkFirstInteraction.value = true
    
    // UI 状态
    errorMessage.value = null
    closeAllMenus()
    resetSeekingState()
  }

  // 兼容旧代码的 reactive 对象访问方式
  const media = computed(() => ({
    playing: playing.value,
    canPlay: canPlay.value,
    seeking: seeking.value,
    loading: loading.value,
    loadingStage: loadingStage.value,
    volume: volume.value,
    muted: muted.value,
    currentTime: currentTime.value,
    duration: duration.value,
    bufferedProgress: bufferedProgress.value,
    firstInteraction: firstInteraction.value,
    playbackRate: playbackRate.value,
    subtitlesEnabled: subtitlesEnabled.value,
    pictureInPicture: pictureInPicture.value,
    hasStartedPlayback: hasStartedPlayback.value,
    currentQuality: currentQuality.value,
    currentSubtitle: currentSubtitle.value,
    autoplay: autoplay.value,
    autoplayNext: autoplayNext.value,
    loop: loop.value,
    subtitleSettings: subtitleSettings.value
  }))

  const ui = computed(() => ({
    controlsVisible: controlsVisible.value,
    fullscreen: fullscreen.value,
    theaterMode: theaterMode.value,
    showPlayIndicator: showPlayIndicator.value,
    isDragging: isDragging.value,
    errorMessage: errorMessage.value,
    showPlaybackRateMenu: showPlaybackRateMenu.value,
    showQualityMenu: showQualityMenu.value,
    showSettingsMenu: showSettingsMenu.value,
    showSubtitlesMenu: showSubtitlesMenu.value,
    showKeyboardHelp: showKeyboardHelp.value,
    showKeyboardFeedback: showKeyboardFeedback.value,
    keyboardFeedback: keyboardFeedback.value,
    seeking: seekingState.value,
    volume: volumeState.value
  }))

  const network = computed(() => ({
    reconnectAttempts: reconnectAttempts.value,
    firstInteraction: networkFirstInteraction.value
  }))

  return {
    // State refs (for direct access)
    playing,
    canPlayVideo,
    canPlayAudio,
    seekingVideo,
    seekingAudio,
    loading,
    loadingStage,
    volume,
    muted,
    currentTime,
    duration,
    bufferedProgress,
    firstInteraction,
    playbackRate,
    subtitlesEnabled,
    pictureInPicture,
    hasStartedPlayback,
    currentQuality,
    currentSubtitle,
    autoplay,
    autoplayNext,
    loop,
    subtitleSettings,
    controlsVisible,
    fullscreen,
    theaterMode,
    showPlayIndicator,
    isDragging,
    errorMessage,
    showPlaybackRateMenu,
    showQualityMenu,
    showSettingsMenu,
    showSubtitlesMenu,
    showKeyboardHelp,
    showKeyboardFeedback,
    keyboardFeedback,
    seekingState,
    volumeState,
    reconnectAttempts,
    networkFirstInteraction,

    // Computed (getters)
    canPlay,
    seeking,
    progress,
    volumeIcon,
    fullscreenIcon,
    loadingStatusText,
    media,
    ui,
    network,

    // Actions
    setPlaying,
    setCanPlay,
    setSeeking,
    setLoading,
    setVolume,
    setMuted,
    toggleMute,
    setCurrentTime,
    setDuration,
    setBufferedProgress,
    setPlaybackRate,
    setCurrentQuality,
    setSubtitlesEnabled,
    toggleSubtitles,
    setCurrentSubtitle,
    updateSubtitleSettings,
    setAutoplay,
    setAutoplayNext,
    setLoop,
    setPictureInPicture,
    setHasStartedPlayback,
    setControlsVisible,
    setFullscreen,
    toggleFullscreen,
    setTheaterMode,
    toggleTheaterMode,
    setShowPlayIndicator,
    setIsDragging,
    setShowMenu,
    closeAllMenus,
    setShowKeyboardHelp,
    showKeyboardFeedbackMessage,
    updateSeekingState,
    resetSeekingState,
    updateVolumeState,
    incrementReconnectAttempts,
    resetReconnectAttempts,
    setNetworkFirstInteraction,
    resetForNewVideo
  }
})
