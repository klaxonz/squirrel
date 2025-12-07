import { defineStore } from 'pinia'
import { ref, computed, type Ref, type ComputedRef } from 'vue'
import type { VideoSubtitle, SeekingState, VolumeState } from '../types/video-player'

/**
 * 字幕设置接口
 */
export interface SubtitleSettings {
  fontSize: 'small' | 'medium' | 'large'
  color: string
  bgOpacity: number
  position: 'top' | 'bottom'
  shadow: boolean
}

/**
 * 加载阶段类型
 */
export type LoadingStage = 'idle' | 'fetching' | 'buffering' | 'ready'

/**
 * Player Store 类型定义
 */
export interface PlayerStoreState {
  // Media State
  playing: boolean
  canPlayVideo: boolean
  canPlayAudio: boolean
  seekingVideo: boolean
  seekingAudio: boolean
  loading: boolean
  loadingStage: LoadingStage
  volume: number
  muted: boolean
  currentTime: number
  duration: number
  bufferedProgress: number
  firstInteraction: boolean
  playbackRate: number
  subtitlesEnabled: boolean
  pictureInPicture: boolean
  hasStartedPlayback: boolean
  currentQuality: string | null
  currentSubtitle: VideoSubtitle | null
  autoplay: boolean
  autoplayNext: boolean
  loop: boolean
  subtitleSettings: SubtitleSettings

  // UI State
  controlsVisible: boolean
  fullscreen: boolean
  theaterMode: boolean
  showPlayIndicator: boolean
  isDragging: boolean
  errorMessage: string | null
  showPlaybackRateMenu: boolean
  showQualityMenu: boolean
  showSettingsMenu: boolean
  showSubtitlesMenu: boolean
  showKeyboardHelp: boolean
  showKeyboardFeedback: boolean
  keyboardFeedback: string
  seekingState: SeekingState
  volumeState: VolumeState

  // Network State
  reconnectAttempts: number
  networkFirstInteraction: boolean
}

/**
 * 默认快进快退状态
 */
const defaultSeekingState: SeekingState = {
  active: false,
  startX: 0,
  currentX: 0,
  distance: 0,
  direction: null,
  seekTime: 0,
  wasPlaying: false
}

/**
 * 默认音量状态
 */
const defaultVolumeState: VolumeState = {
  adjusting: false,
  startY: 0,
  startVolume: 0,
  showIndicator: false
}

/**
 * 默认字幕设置
 */
const defaultSubtitleSettings: SubtitleSettings = {
  fontSize: 'medium',
  color: 'white',
  bgOpacity: 0.4,
  position: 'bottom',
  shadow: true
}

/**
 * Player Store
 * 使用 Pinia Composition API 定义
 */
export const usePlayerStore = defineStore('player', () => {
  // ========== Media State ==========
  const playing: Ref<boolean> = ref(false)
  const canPlayVideo: Ref<boolean> = ref(false)
  const canPlayAudio: Ref<boolean> = ref(false)
  const seekingVideo: Ref<boolean> = ref(false)
  const seekingAudio: Ref<boolean> = ref(false)
  const loading: Ref<boolean> = ref(false)
  const loadingStage: Ref<LoadingStage> = ref('idle')
  const volume: Ref<number> = ref(100)
  const muted: Ref<boolean> = ref(false)
  const currentTime: Ref<number> = ref(0)
  const duration: Ref<number> = ref(0)
  const bufferedProgress: Ref<number> = ref(0)
  const firstInteraction: Ref<boolean> = ref(true)
  const playbackRate: Ref<number> = ref(1)
  const subtitlesEnabled: Ref<boolean> = ref(false)
  const pictureInPicture: Ref<boolean> = ref(false)
  const hasStartedPlayback: Ref<boolean> = ref(false)
  const currentQuality: Ref<string | null> = ref(null)
  const currentSubtitle: Ref<VideoSubtitle | null> = ref(null)
  const autoplay: Ref<boolean> = ref(false)
  const autoplayNext: Ref<boolean> = ref(true)
  const loop: Ref<boolean> = ref(false)
  const subtitleSettings: Ref<SubtitleSettings> = ref({ ...defaultSubtitleSettings })

  // ========== UI State ==========
  const controlsVisible: Ref<boolean> = ref(true)
  const fullscreen: Ref<boolean> = ref(false)
  const theaterMode: Ref<boolean> = ref(false)
  const showPlayIndicator: Ref<boolean> = ref(false)
  const isDragging: Ref<boolean> = ref(false)
  const errorMessage: Ref<string | null> = ref(null)
  const showPlaybackRateMenu: Ref<boolean> = ref(false)
  const showQualityMenu: Ref<boolean> = ref(false)
  const showSettingsMenu: Ref<boolean> = ref(false)
  const showSubtitlesMenu: Ref<boolean> = ref(false)
  const showKeyboardHelp: Ref<boolean> = ref(false)
  const showKeyboardFeedback: Ref<boolean> = ref(false)
  const keyboardFeedback: Ref<string> = ref('')
  const seekingState: Ref<SeekingState> = ref({ ...defaultSeekingState })
  const volumeState: Ref<VolumeState> = ref({ ...defaultVolumeState })

  // ========== Network State ==========
  const reconnectAttempts: Ref<number> = ref(0)
  const networkFirstInteraction: Ref<boolean> = ref(true)

  // ========== Computed (Getters) ==========
  const canPlay: ComputedRef<{ video: boolean; audio: boolean }> = computed(() => ({
    video: canPlayVideo.value,
    audio: canPlayAudio.value
  }))

  const seeking: ComputedRef<{ video: boolean; audio: boolean }> = computed(() => ({
    video: seekingVideo.value,
    audio: seekingAudio.value
  }))

  const progress: ComputedRef<number> = computed(() => {
    return (currentTime.value / duration.value) * 100 || 0
  })

  const volumeIcon: ComputedRef<string> = computed(() => {
    if (muted.value || volume.value === 0) return 'material-symbols:volume-off'
    if (volume.value < 50) return 'material-symbols:volume-down'
    return 'material-symbols:volume-up'
  })

  const fullscreenIcon: ComputedRef<string> = computed(() =>
    fullscreen.value ? 'material-symbols:fullscreen-exit' : 'material-symbols:fullscreen'
  )

  const loadingStatusText: ComputedRef<string> = computed(() => {
    switch (loadingStage.value) {
      case 'fetching': return '获取视频链接中...'
      case 'buffering': return '缓冲中...'
      case 'ready': return '准备就绪'
      default: return '加载中...'
    }
  })

  // ========== Actions ==========
  
  // Media actions
  function setPlaying(value: boolean): void {
    playing.value = value
  }

  function setCanPlay(type: 'video' | 'audio', value: boolean): void {
    if (type === 'video') canPlayVideo.value = value
    else if (type === 'audio') canPlayAudio.value = value
  }

  function setSeeking(type: 'video' | 'audio', value: boolean): void {
    if (type === 'video') seekingVideo.value = value
    else if (type === 'audio') seekingAudio.value = value
  }

  function setLoading(value: boolean, stage: LoadingStage | string | null = null): void {
    loading.value = value
    if (stage !== null) loadingStage.value = stage as LoadingStage
  }

  function setVolume(value: number): void {
    volume.value = Math.max(0, Math.min(100, value))
  }

  function setMuted(value: boolean): void {
    muted.value = value
  }

  function toggleMute(): void {
    muted.value = !muted.value
  }

  function setCurrentTime(value: number): void {
    currentTime.value = value
  }

  function setDuration(value: number): void {
    duration.value = value
  }

  function setBufferedProgress(value: number): void {
    bufferedProgress.value = value
  }

  function setPlaybackRate(value: number): void {
    playbackRate.value = value
  }

  function setCurrentQuality(value: string | null): void {
    currentQuality.value = value
  }

  function setSubtitlesEnabled(value: boolean): void {
    subtitlesEnabled.value = value
  }

  function toggleSubtitles(): void {
    subtitlesEnabled.value = !subtitlesEnabled.value
  }

  function setCurrentSubtitle(value: VideoSubtitle | null): void {
    currentSubtitle.value = value
  }

  function updateSubtitleSettings(settings: Partial<SubtitleSettings>): void {
    subtitleSettings.value = { ...subtitleSettings.value, ...settings }
  }

  function setAutoplay(value: boolean): void {
    autoplay.value = value
  }

  function setAutoplayNext(value: boolean): void {
    autoplayNext.value = value
  }

  function setLoop(value: boolean): void {
    loop.value = value
  }

  function setPictureInPicture(value: boolean): void {
    pictureInPicture.value = value
  }

  function setHasStartedPlayback(value: boolean): void {
    hasStartedPlayback.value = value
  }

  // UI actions
  function setControlsVisible(value: boolean): void {
    controlsVisible.value = value
  }

  function setFullscreen(value: boolean): void {
    fullscreen.value = value
  }

  function toggleFullscreen(): void {
    fullscreen.value = !fullscreen.value
  }

  function setTheaterMode(value: boolean): void {
    theaterMode.value = value
  }

  function toggleTheaterMode(): void {
    theaterMode.value = !theaterMode.value
  }

  function setShowPlayIndicator(value: boolean): void {
    showPlayIndicator.value = value
  }

  function setIsDragging(value: boolean): void {
    isDragging.value = value
  }

  function setShowMenu(menuName: string, value: boolean): void {
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

  function closeAllMenus(): void {
    showPlaybackRateMenu.value = false
    showQualityMenu.value = false
    showSettingsMenu.value = false
    showSubtitlesMenu.value = false
  }

  function setShowKeyboardHelp(value: boolean): void {
    showKeyboardHelp.value = value
  }

  function showKeyboardFeedbackMessage(message: string): void {
    keyboardFeedback.value = message
    showKeyboardFeedback.value = true
    setTimeout(() => {
      showKeyboardFeedback.value = false
    }, 1000)
  }

  function updateSeekingState(updates: Partial<SeekingState>): void {
    seekingState.value = { ...seekingState.value, ...updates }
  }

  function resetSeekingState(): void {
    seekingState.value = { ...defaultSeekingState }
  }

  function updateVolumeState(updates: Partial<VolumeState>): void {
    volumeState.value = { ...volumeState.value, ...updates }
  }

  // Network actions
  function incrementReconnectAttempts(): void {
    reconnectAttempts.value++
  }

  function resetReconnectAttempts(): void {
    reconnectAttempts.value = 0
  }

  function setNetworkFirstInteraction(value: boolean): void {
    networkFirstInteraction.value = value
  }

  // Reset all state (when switching videos)
  function resetForNewVideo(): void {
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

/**
 * 导出 Store 类型，用于类型推断
 */
export type PlayerStore = ReturnType<typeof usePlayerStore>
