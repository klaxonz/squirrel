<template>
  <div class="video-wrapper bg-[#0f0f0f]">
    <div
      class="video-player-container"
      @pointerenter="onPointerEnter"
      @pointerleave="onPointerLeave"
      @pointermove="onPointerMove"
      @keydown="handleKeyDown"
      tabindex="0"
      role="application"
      aria-label="视频播放器"
    >
      <!-- 加载状态 -->
      <LoadingSpinner
        v-if="playerState.media.loading"
        :loading-text="loadingStatusText"
        :network-speed="formatNetworkSpeed(performanceState.bandwidth.current)"
      />

      <!-- 视频核心 -->
      <VideoPlayerCore
        ref="videoCore"
        :video="video"
        :player-state="playerState"
        :is-hls-stream="isHlsStream"
        @play="handleVideoPlay"
        @pause="handleVideoPause"
        @timeupdate="handleVideoTimeupdate"
        @error="handleVideoError"
        @click="handleVideoLayerClick"
        @skip-forward="skipForward"
        @skip-backward="skipBackward"
      />

      <!-- 缓冲指示器 -->
      <BufferingIndicator
        :is-buffering="playerState.media.loading && playerState.media.loadingStage === 'buffering'"
      />

      <!-- 播放覆盖层 -->
      <PlayOverlay
        :playing="playerState.media.playing"
        :loading="playerState.media.loading"
        @play="togglePlay"
      />

      <!-- 控制栏 -->
      <VideoControls
        v-show="playerState.ui.controlsVisible"
        :player-state="playerState"
        :video="video"
        :progress="progress"
        :volume-icon="volumeIcon"
        :fullscreen-icon="fullscreenIcon"
        :supports-pip="supportsPiP"
        :available-qualities="availableQualities"
        :playback-rates="playbackRates"
        @toggle-play="togglePlay"
        @skip-forward="skipForward"
        @skip-backward="skipBackward"
        @toggle-mute="toggleMute"
        @toggle-fullscreen="toggleFullscreen"
        @toggle-subtitles="toggleSubtitles"
        @toggle-theater="toggleTheaterMode"
        @toggle-pip="togglePictureInPicture"
        @set-quality="setQuality"
        @set-playback-rate="setPlaybackRate"
        @set-subtitle="setSubtitle"
        @progress-seek="setVideoTime"
      />
      <!-- 错误消息 -->
      <ErrorMessage
        v-if="errorState.hasError"
        :error-state="errorState"
        :error-info="getErrorInfo()"
        @retry="handleRetry"
        @report="reportErrorToSupport"
        @dismiss="dismissError"
      />

      <!-- 快进/快退指示器 -->
      <SeekingIndicator
        v-if="playerState.ui.seeking.active"
        :seeking-state="playerState.ui.seeking"
      />

      <!-- 音量调节指示器 -->
      <VolumeIndicator
        v-if="playerState.ui.volume.showIndicator"
        :volume="playerState.media.volume"
      />

      <!-- 键盘帮助 -->
      <KeyboardHelp
        v-if="playerState.ui.showKeyboardHelp"
        @close="toggleKeyboardHelp"
      />
    </div>
  </div>
</template>

<script setup>
import VideoPlayerCore from './VideoPlayerCore.vue'
import VideoControls from './VideoControls.vue'
import LoadingSpinner from './LoadingSpinner.vue'
import ErrorMessage from './ErrorMessage.vue'
import SeekingIndicator from './SeekingIndicator.vue'
import VolumeIndicator from './VolumeIndicator.vue'
import KeyboardHelp from './KeyboardHelp.vue'
import BufferingIndicator from './BufferingIndicator.vue'
import PlayOverlay from './PlayOverlay.vue'

import useVideoPlayer from '../../composables/useVideoPlayer.js'
import useVideoControls from '../../composables/useVideoControls.js'
import useKeyboardShortcuts from '../../composables/useKeyboardShortcuts.js'

const props = defineProps({
  video: Object
})

const emit = defineEmits(['play', 'pause', 'ended', 'fullscreenChange', 'timeupdate', 'error'])

const {
  playerState,
  performanceState,
  errorState,
  videoCore,
  isHlsStream,
  progress,
  volumeIcon,
  fullscreenIcon,
  supportsPiP,
  loadingStatusText,
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
} = useVideoPlayer(props, emit)

// 使用控制相关的组合函数
const {
  availableQualities,
  playbackRates,
  togglePlay,
  skipForward,
  skipBackward,
  toggleMute,
  toggleFullscreen,
  toggleSubtitles,
  toggleTheaterMode,
  togglePictureInPicture,
  setQuality,
  setPlaybackRate,
  setSubtitle
} = useVideoControls(playerState, videoCore)

// 键盘快捷键
const { handleKeyDown } = useKeyboardShortcuts(playerState, {
  togglePlay,
  skipForward,
  skipBackward,
  setVideoTime,
  toggleMute,
  toggleFullscreen,
  togglePictureInPicture,
  toggleSubtitles,
})

defineExpose({
  videoCore
})




</script>

<style scoped>
.video-wrapper {
  @apply absolute inset-0;
  background: #000000;
}

.video-player-container {
  @apply relative w-full h-full;
  background: #000000;
  overflow: hidden;
}

/* YouTube风格的焦点状态 */
.video-player-container:focus {
  outline: 2px solid rgba(255, 255, 255, 0.3);
  outline-offset: 2px;
}

.video-player-container:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.5);
}
</style>
