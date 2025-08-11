/**
 * VideoPlayer 组件类型定义
 */

// 基础视频信息
export interface VideoInfo {
  id: string
  title: string
  thumbnail?: string
  stream_video_url: string
  stream_audio_url?: string
  total_duration?: number
  last_position?: number
  chapters?: VideoChapter[]
  subtitles?: VideoSubtitle[]
}

// 视频章节
export interface VideoChapter {
  id: string
  title: string
  time: number
  thumbnail?: string
}

// 字幕信息
export interface VideoSubtitle {
  id: string
  language: string
  label: string
  url: string
  default?: boolean
}

// 播放器媒体状态
export interface MediaState {
  playing: boolean
  canPlay: {
    video: boolean
    audio: boolean
  }
  seeking: {
    video: boolean
    audio: boolean
  }
  loading: boolean
  loadingStage: 'idle' | 'fetching' | 'buffering' | 'ready'
  volume: number
  muted: boolean
  currentTime: number
  duration: number
  bufferedProgress: number
  firstInteraction: boolean
  playbackRate: number
  subtitlesEnabled: boolean
  pictureInPicture: boolean
  currentQuality: string
  currentSubtitle: VideoSubtitle | null
  autoplay: boolean
  loop: boolean
}

// 播放器UI状态
export interface UIState {
  controlsVisible: boolean
  fullscreen: boolean
  showPlayIndicator: boolean
  isDragging: boolean
  errorMessage: string | null
  showPlaybackRateMenu: boolean
  showSettingsMenu: boolean
  showKeyboardHelp: boolean
  showKeyboardFeedback: boolean
  keyboardFeedback: string
  seeking: SeekingState
  volume: VolumeState
}

// 快进快退状态
export interface SeekingState {
  active: boolean
  startX: number
  currentX: number
  distance: number
  direction: 'forward' | 'backward' | null
  seekTime: number
  wasPlaying: boolean
}

// 音量调节状态
export interface VolumeState {
  adjusting: boolean
  startY: number
  startVolume: number
  showIndicator: boolean
}

// 网络状态
export interface NetworkState {
  reconnectAttempts: number
  firstInteraction: boolean
}

// 完整的播放器状态
export interface PlayerState {
  media: MediaState
  ui: UIState
  network: NetworkState
}

// 性能监控状态
export interface PerformanceState {
  bandwidth: {
    samples: number[]
    average: number
    current: number
  }
  memory: {
    used: number
    peak: number
    lastCleanup: number
  }
  loading: {
    startTime: number
    duration: number
    bytesLoaded: number
  }
}

// 错误状态
export interface ErrorState {
  hasError: boolean
  errorType: string | null
  errorMessage: string | null
  canRetry: boolean
  retryCount: number
  maxRetries: number
  lastErrorTime: number
}

// 错误信息
export interface ErrorInfo {
  title: string
  message: string
  suggestions?: string[]
  code?: string
  details?: Record<string, any>
}

// 质量选项
export interface QualityOption {
  value: string
  label: string
  bitrate?: number
  resolution?: string
}

// 播放器事件
export interface PlayerEvents {
  play: () => void
  pause: () => void
  ended: () => void
  timeupdate: (currentTime: number) => void
  error: (error: { type: string; error: any; errorInfo?: ErrorInfo }) => void
  fullscreenChange: (isFullscreen: boolean) => void
  qualityChange: (quality: string) => void
  subtitleChange: (subtitle: VideoSubtitle | null) => void
  playbackRateChange: (rate: number) => void
  volumeChange: (volume: number) => void
}

// 进度条事件
export interface ProgressBarEvents {
  seek: (time: number) => void
}

// 控制按钮事件
export interface ControlEvents {
  'toggle-play': () => void
  'skip-forward': () => void
  'skip-backward': () => void
  'toggle-mute': () => void
  'toggle-fullscreen': () => void
  'toggle-subtitles': () => void
  'toggle-pip': () => void
  'set-quality': (quality: string) => void
  'set-playback-rate': (rate: number) => void
  'set-subtitle': (subtitle: VideoSubtitle | null) => void
  'volume-change': (volume: number) => void
}

// 键盘快捷键配置
export interface KeyboardShortcut {
  key: string
  ctrlKey?: boolean
  shiftKey?: boolean
  altKey?: boolean
  action: string
  description: string
}

// 播放器配置
export interface PlayerConfig {
  autoplay?: boolean
  muted?: boolean
  loop?: boolean
  preload?: 'none' | 'metadata' | 'auto'
  playbackRates?: number[]
  defaultQuality?: string
  enableKeyboardShortcuts?: boolean
  enablePictureInPicture?: boolean
  enableFullscreen?: boolean
  showControls?: boolean
  controlsTimeout?: number
  theme?: 'dark' | 'light' | 'auto'
}

// HLS配置
export interface HLSConfig {
  enableWorker?: boolean
  lowLatencyMode?: boolean
  backBufferLength?: number
  maxBufferLength?: number
  maxMaxBufferLength?: number
  maxBufferSize?: number
  maxBufferHole?: number
  highBufferWatchdogPeriod?: number
  nudgeOffset?: number
  nudgeMaxRetry?: number
  maxFragLookUpTolerance?: number
  liveSyncDurationCount?: number
  liveMaxLatencyDurationCount?: number
  enableSoftwareAES?: boolean
}

// 组合函数返回类型
export interface UseVideoPlayerReturn {
  playerState: PlayerState
  performanceState: PerformanceState
  errorState: ErrorState
  videoCore: any
  isHlsStream: boolean
  hasAudioStream: boolean
  isCanplay: boolean
  volumeIcon: string
  fullscreenIcon: string
  progress: number
  supportsPiP: boolean
  loadingStatusText: string
  formatNetworkSpeed: (bytesPerSecond: number) => string
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

export interface UseVideoControlsReturn {
  availableQualities: QualityOption[]
  playbackRates: number[]
  togglePlay: () => void
  skipForward: () => void
  skipBackward: () => void
  setVideoTime: (time: number) => void
  toggleMute: () => void
  adjustVolume: (delta: number) => void
  toggleFullscreen: () => Promise<void>
  togglePictureInPicture: () => Promise<void>
  toggleSubtitles: () => void
  setSubtitle: (subtitle: VideoSubtitle | null) => void
  setPlaybackRate: (rate: number) => void
  adjustPlaybackRate: (delta: number) => void
  setQuality: (quality: string) => void
  seekToPercentage: (percentage: number) => void
}
