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
        v-if="playerState.media.loading && playerState.media.loadingStage !== 'buffering'"
        :loading-text="loadingStatusText"
        :network-speed="formatNetworkSpeed(performanceState.bandwidth.current)"
      />


      <!-- 视频核心 -->
      <VideoPlayerCore
        ref="videoCore"
        :video="video"
        :player-state="playerState"
        :is-hls-stream="isHlsStream"
        :is-dash-stream="isDashStream"
        :on-bandwidth-sample="updateBandwidth"
        :external-error="getErrorInfo()"
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
        :network-speed="formatNetworkSpeed(performanceState.bandwidth.current)"
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
        @seek-start="onSeekStart"
        @progress-seek="setVideoTime"
        @seek-end="onSeekEnd"
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
import { computed, watch } from 'vue'
import VideoPlayerCore from './VideoPlayerCore.vue'
import VideoControls from './VideoControls.vue'
import LoadingSpinner from './LoadingSpinner.vue'
import SeekingIndicator from './SeekingIndicator.vue'
import VolumeIndicator from './VolumeIndicator.vue'
import KeyboardHelp from './KeyboardHelp.vue'
import BufferingIndicator from './BufferingIndicator.vue'
import PlayOverlay from './PlayOverlay.vue'

import useVideoPlayer from '../../composables/useVideoPlayer.js'
import useVideoControls from '../../composables/useVideoControls.js'
import useKeyboardShortcuts from '../../composables/useKeyboardShortcuts.js'
import useSubtitles from '../../composables/useSubtitles.js'

const props = defineProps({
  video: Object
})

const emit = defineEmits(['play', 'pause', 'ended', 'fullscreenChange', 'timeupdate', 'error'])

const {
  playerState,
  performanceState,
  videoCore,
  isHlsStream,
  isDashStream,
  progress,
  volumeIcon,
  fullscreenIcon,
  supportsPiP,
  loadingStatusText,
  formatNetworkSpeed,
  updateBandwidth,
  handleVideoPlay,
  handleVideoPause,
  handleVideoTimeupdate,
  handleVideoError,
  handleVideoLayerClick,
  setVideoTime,
  getErrorInfo,
  onPointerEnter,
  onPointerLeave,
  onPointerMove,
} = useVideoPlayer(props, emit)

// 字幕集成：将 VideoCore 的 videoElement 作为字幕的 videoRef
const videoElRef = computed(() => videoCore.value?.videoElement || null)
const { toggleSubtitles, setSubtitle, ensureSubtitlesOnMetadata } = useSubtitles({
  playerState,
  videoRef: videoElRef,
  props
})

// 元数据就绪时确保字幕加载
watch(() => playerState.media.canPlay.video, (val) => {
  if (val) {
    try { ensureSubtitlesOnMetadata() } catch (e) {}
  }
})

// 使用控制相关的组合函数
const {
  availableQualities,
  playbackRates,
  togglePlay,
  skipForward,
  skipBackward,
  toggleMute,
  toggleFullscreen,
  toggleTheaterMode,
  togglePictureInPicture,
  toggleKeyboardHelp,
  adjustVolume,
  adjustPlaybackRate,
  setQuality,
  setPlaybackRate
} = useVideoControls(playerState, videoCore)

// 拖动进度条时的暂停/恢复
const onSeekStart = () => {
  if (!videoCore.value?.videoElement) return
  playerState.ui.isDragging = true
  // 记录是否在播放
  playerState.ui.seeking.wasPlaying = !!playerState.media.playing
  // 暂停视频和音频，避免拖动时继续播放导致不同步
  try { videoCore.value.videoElement.pause() } catch (e) {}
  if (videoCore.value.audioElement) {
    try { videoCore.value.audioElement.pause() } catch (e) {}
  }
}

const onSeekEnd = async () => {
  playerState.ui.isDragging = false
  // 拖动结束，如之前在播放则恢复
  if (playerState.ui.seeking.wasPlaying) {
    try {
      await videoCore.value?.videoElement?.play()
      if (videoCore.value?.audioElement) {
        try { await videoCore.value.audioElement.play() } catch (e) { console.warn('Audio resume failed:', e) }
      }
    } catch (e) {
      console.warn('Video resume failed:', e)
    }
  }
}

// 键盘快捷键
const { handleKeyDown } = useKeyboardShortcuts(playerState, {
  togglePlay,
  skipForward,
  skipBackward,
  setVideoTime,
  toggleMute,
  adjustVolume,
  adjustPlaybackRate,
  toggleFullscreen,
  togglePictureInPicture,
  toggleSubtitles,
  toggleKeyboardHelp,
  handleEscapeKey: () => {
    if (playerState.ui.showKeyboardHelp) {
      playerState.ui.showKeyboardHelp = false
    } else if (playerState.ui.fullscreen) {
      toggleFullscreen()
    }
  },
  getDuration: () => playerState.media.duration,
  getCurrentTime: () => playerState.media.currentTime
})

defineExpose({
  videoCore
})




</script>

<style scoped>
.video-wrapper {
  position: absolute; inset: 0; background: #000;
}

.video-player-container {
  position: relative; width: 100%; height: 100%;
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

/* 全屏状态下的样式修复 */
.video-player-container:fullscreen,
.video-player-container:-webkit-full-screen,
.video-player-container:-moz-full-screen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw !important;
  height: 100vh !important;
  z-index: 2147483647;
  background: #000000;
}

/* 确保全屏状态下视频元素正确填充 */
.video-player-container:fullscreen .video-player,
.video-player-container:-webkit-full-screen .video-player,
.video-player-container:-moz-full-screen .video-player {
  width: 100% !important;
  height: 100% !important;
  object-fit: contain;
}
</style>
