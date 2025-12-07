import { provide, inject, computed } from 'vue'

// Provide/Inject key
export const PLAYER_CONTEXT_KEY = Symbol('playerContext')

/**
 * 在 VideoPlayer 中调用，提供播放器上下文
 */
export function providePlayerContext(context) {
  provide(PLAYER_CONTEXT_KEY, context)
}

/**
 * 在子组件中调用，获取播放器上下文
 */
export function usePlayerContext() {
  const context = inject(PLAYER_CONTEXT_KEY)
  if (!context) {
    console.warn('[usePlayerContext] No player context provided')
    return null
  }
  return context
}

/**
 * 创建播放器上下文对象
 */
export function createPlayerContext({
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
}) {
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
  }
}
