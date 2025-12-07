import { provide, inject, computed, type ComputedRef, type Ref } from 'vue'
import type { 
  VideoInfo, 
  VideoSubtitle, 
  QualityOption,
  SeekingState,
  VolumeState
} from '../types/video-player'

// Provide/Inject key
export const PLAYER_CONTEXT_KEY = Symbol('playerContext')

/**
 * 播放器上下文接口定义
 */
export interface PlayerContext {
  // Store - Pinia store 实例
  store: PlayerStore

  // Refs
  videoCore: Ref<VideoPlayerCoreInstance | null>

  // Props (wrapped as computed for reactivity)
  video: ComputedRef<VideoInfo | undefined>
  hasPrev: ComputedRef<boolean>
  hasNext: ComputedRef<boolean>

  // Computed - 流媒体类型
  isHlsStream: ComputedRef<boolean>
  isDashStream: ComputedRef<boolean>
  isCanplay: ComputedRef<boolean>

  // Computed - 播放状态
  progress: ComputedRef<number>
  volumeIcon: ComputedRef<string>
  fullscreenIcon: ComputedRef<string>
  supportsPiP: ComputedRef<boolean>
  loadingStatusText: ComputedRef<string>

  // Computed - 可用选项
  availableQualities: Ref<QualityOption[]>
  playbackRates: ComputedRef<number[]>

  // Methods - 格式化
  formatNetworkSpeed: (bps: number) => string
  updateBandwidth: (loaded: number, durationSec: number) => void

  // Playback controls
  togglePlay: () => void
  skipForward: () => void
  skipBackward: () => void
  setVideoTime: (time: number) => void

  // Volume controls
  toggleMute: () => void
  adjustVolume: (delta: number) => void

  // Display controls
  toggleFullscreen: () => Promise<void>
  toggleTheaterMode: () => void
  togglePictureInPicture: () => Promise<void>
  toggleKeyboardHelp: () => void

  // Subtitle controls
  toggleSubtitles: () => void
  setSubtitle: (subtitle: VideoSubtitle | null) => void

  // Settings
  setPlaybackRate: (rate: number) => void
  adjustPlaybackRate: (delta: number) => void
  setQuality: (quality: string) => void
  updateAvailableQualities: (qualities: QualityOption[]) => void

  // Seek controls
  onSeekStart: () => void
  onSeekEnd: () => Promise<void>

  // Navigation
  onPrevVideo: () => void
  onNextVideo: () => void
}

/**
 * VideoPlayerCore 组件实例接口
 */
export interface VideoPlayerCoreInstance {
  videoElement: HTMLVideoElement | null
  audioElement: HTMLAudioElement | null
  reinitSources?: () => void
}

/**
 * Pinia Player Store 接口
 * 注意: 这里只定义上下文需要用到的部分，完整类型在 playerStore.ts 中
 */
export interface PlayerStore {
  // Media state
  playing: boolean
  canPlayVideo: boolean
  canPlayAudio: boolean
  seekingVideo: boolean
  seekingAudio: boolean
  loading: boolean
  loadingStage: 'idle' | 'fetching' | 'buffering' | 'ready'
  volume: number
  muted: boolean
  currentTime: number
  duration: number
  bufferedProgress: number
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

  // UI state
  controlsVisible: boolean
  fullscreen: boolean
  theaterMode: boolean
  showPlayIndicator: boolean
  isDragging: boolean
  showPlaybackRateMenu: boolean
  showQualityMenu: boolean
  showSettingsMenu: boolean
  showSubtitlesMenu: boolean
  showKeyboardHelp: boolean
  showKeyboardFeedback: boolean
  keyboardFeedback: string
  seekingState: SeekingState
  volumeState: VolumeState

  // Network state
  reconnectAttempts: number
  networkFirstInteraction: boolean

  // Computed
  progress: number
  volumeIcon: string
  fullscreenIcon: string
  loadingStatusText: string

  // Actions
  setPlaying: (value: boolean) => void
  setCanPlay: (type: 'video' | 'audio', value: boolean) => void
  setSeeking: (type: 'video' | 'audio', value: boolean) => void
  setLoading: (value: boolean, stage?: string | null) => void
  setVolume: (value: number) => void
  setMuted: (value: boolean) => void
  toggleMute: () => void
  setCurrentTime: (value: number) => void
  setDuration: (value: number) => void
  setBufferedProgress: (value: number) => void
  setPlaybackRate: (value: number) => void
  setCurrentQuality: (value: string | null) => void
  setSubtitlesEnabled: (value: boolean) => void
  toggleSubtitles: () => void
  setCurrentSubtitle: (value: VideoSubtitle | null) => void
  updateSubtitleSettings: (settings: Partial<SubtitleSettings>) => void
  setAutoplay: (value: boolean) => void
  setAutoplayNext: (value: boolean) => void
  setLoop: (value: boolean) => void
  setPictureInPicture: (value: boolean) => void
  setHasStartedPlayback: (value: boolean) => void
  setControlsVisible: (value: boolean) => void
  setFullscreen: (value: boolean) => void
  toggleFullscreen: () => void
  setTheaterMode: (value: boolean) => void
  toggleTheaterMode: () => void
  setShowPlayIndicator: (value: boolean) => void
  setIsDragging: (value: boolean) => void
  setShowMenu: (menuName: string, value: boolean) => void
  closeAllMenus: () => void
  setShowKeyboardHelp: (value: boolean) => void
  showKeyboardFeedbackMessage: (message: string) => void
  updateSeekingState: (updates: Partial<SeekingState>) => void
  resetSeekingState: () => void
  updateVolumeState: (updates: Partial<VolumeState>) => void
  incrementReconnectAttempts: () => void
  resetReconnectAttempts: () => void
  setNetworkFirstInteraction: (value: boolean) => void
  resetForNewVideo: () => void
}

export interface SubtitleSettings {
  fontSize: 'small' | 'medium' | 'large'
  color: string
  bgOpacity: number
  position: 'top' | 'bottom'
  shadow: boolean
}

/**
 * 创建播放器上下文的参数接口
 */
export interface CreatePlayerContextParams {
  // Store
  store: PlayerStore

  // Refs
  videoCore: Ref<VideoPlayerCoreInstance | null>

  // Props
  video: VideoInfo | undefined
  hasPrev: boolean
  hasNext: boolean

  // Computed
  isHlsStream: ComputedRef<boolean>
  isDashStream: ComputedRef<boolean>
  isCanplay: ComputedRef<boolean>
  progress: ComputedRef<number>
  volumeIcon: ComputedRef<string>
  fullscreenIcon: ComputedRef<string>
  supportsPiP: ComputedRef<boolean>
  loadingStatusText: ComputedRef<string>
  availableQualities: Ref<QualityOption[]>
  playbackRates: number[]

  // Methods
  formatNetworkSpeed: (bps: number) => string
  updateBandwidth: (loaded: number, durationSec: number) => void

  // Playback controls
  togglePlay: () => void
  skipForward: () => void
  skipBackward: () => void
  setVideoTime: (time: number) => void

  // Volume controls
  toggleMute: () => void
  adjustVolume: (delta: number) => void

  // Display controls
  toggleFullscreen: () => Promise<void>
  toggleTheaterMode: () => void
  togglePictureInPicture: () => Promise<void>
  toggleKeyboardHelp: () => void

  // Subtitle controls
  toggleSubtitles: () => void
  setSubtitle: (subtitle: VideoSubtitle | null) => void

  // Settings
  setPlaybackRate: (rate: number) => void
  adjustPlaybackRate: (delta: number) => void
  setQuality: (quality: string) => void
  updateAvailableQualities: (qualities: QualityOption[]) => void

  // Seek controls
  onSeekStart: () => void
  onSeekEnd: () => Promise<void>

  // Navigation
  onPrevVideo: () => void
  onNextVideo: () => void
}

/**
 * 在 VideoPlayer 中调用，提供播放器上下文
 */
export function providePlayerContext(context: PlayerContext): void {
  provide(PLAYER_CONTEXT_KEY, context)
}

/**
 * 在子组件中调用，获取播放器上下文
 * @returns PlayerContext | null
 */
export function usePlayerContext(): PlayerContext | null {
  const context = inject<PlayerContext>(PLAYER_CONTEXT_KEY)
  if (!context) {
    console.warn('[usePlayerContext] No player context provided')
    return null
  }
  return context
}

/**
 * 创建播放器上下文对象
 */
export function createPlayerContext(params: CreatePlayerContextParams): PlayerContext {
  const {
    // Store
    store,

    // Refs
    videoCore,

    // Props
    video,
    hasPrev,
    hasNext,

    // Computed
    isHlsStream,
    isDashStream,
    isCanplay,
    progress,
    volumeIcon,
    fullscreenIcon,
    supportsPiP,
    loadingStatusText,
    availableQualities,
    playbackRates,

    // Methods
    formatNetworkSpeed,
    updateBandwidth,

    // Playback controls
    togglePlay,
    skipForward,
    skipBackward,
    setVideoTime,

    // Volume controls
    toggleMute,
    adjustVolume,

    // Display controls
    toggleFullscreen,
    toggleTheaterMode,
    togglePictureInPicture,
    toggleKeyboardHelp,

    // Subtitle controls
    toggleSubtitles,
    setSubtitle,

    // Settings
    setPlaybackRate,
    adjustPlaybackRate,
    setQuality,
    updateAvailableQualities,

    // Seek controls
    onSeekStart,
    onSeekEnd,

    // Navigation
    onPrevVideo,
    onNextVideo
  } = params

  return {
    // Store - 直接访问 Pinia store
    store,

    // Refs
    videoCore,

    // Props (wrapped as computed for reactivity)
    video: computed(() => video),
    hasPrev: computed(() => hasPrev),
    hasNext: computed(() => hasNext),

    // Computed
    isHlsStream,
    isDashStream,
    isCanplay,
    progress,
    volumeIcon,
    fullscreenIcon,
    supportsPiP,
    loadingStatusText,
    availableQualities,
    playbackRates: computed(() => playbackRates),

    // Methods
    formatNetworkSpeed,
    updateBandwidth,

    // Playback controls
    togglePlay,
    skipForward,
    skipBackward,
    setVideoTime,

    // Volume controls
    toggleMute,
    adjustVolume,

    // Display controls
    toggleFullscreen,
    toggleTheaterMode,
    togglePictureInPicture,
    toggleKeyboardHelp,

    // Subtitle controls
    toggleSubtitles,
    setSubtitle,

    // Settings
    setPlaybackRate,
    adjustPlaybackRate,
    setQuality,
    updateAvailableQualities,

    // Seek controls
    onSeekStart,
    onSeekEnd,

    // Navigation
    onPrevVideo,
    onNextVideo
  }
}
