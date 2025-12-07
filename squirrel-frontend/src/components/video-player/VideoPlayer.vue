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
        v-if="store.loading && store.loadingStage !== 'buffering'"
        :loading-text="loadingStatusText"
        :network-speed="formatNetworkSpeed(performanceState.bandwidth.current)"
      />

      <!-- 视频核心 -->
      <VideoPlayerCore
        ref="videoCore"
        :video="video"
        :is-hls-stream="isHlsStream"
        :is-dash-stream="isDashStream"
        :on-bandwidth-sample="updateBandwidth"
        :on-qualities-update="updateAvailableQualities"
        :external-error="props.externalError || getErrorInfo()"
        @play="handleVideoPlay"
        @pause="handleVideoPause"
        @timeupdate="handleVideoTimeupdate"
        @error="handleVideoError"
        @click="handleVideoLayerClick"
        @skip-forward="skipForward"
        @skip-backward="skipBackward"
        @ended="onEnded"
      />

      <!-- 缓冲指示器 -->
      <BufferingIndicator
        :is-buffering="isActiveBuffering"
        :network-speed="formatNetworkSpeed(performanceState.bandwidth.current)"
      />

      <!-- 播放覆盖层 -->
      <PlayOverlay
        :playing="store.playing"
        :loading="store.loading"
        :can-play="isCanplay"
        @play="togglePlay"
      />

      <!-- 加载状态指示器 -->
      <div 
        v-if="store.loading" 
        class="loading-status-indicator"
        :class="{ 'with-controls': store.controlsVisible }"
      >
        <div class="loading-status-text">{{ loadingStatusText }}</div>
      </div>

      <!-- 控制栏 -->
      <VideoControls
        v-show="store.controlsVisible"
        :video="video"
        :progress="progress"
        :volume-icon="volumeIcon"
        :fullscreen-icon="fullscreenIcon"
        :supports-pip="supportsPiP"
        :available-qualities="availableQualities"
        :playback-rates="playbackRates"
        :has-prev="hasPrev"
        :has-next="hasNext"
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
        @prev-video="$emit('prev-video')"
        @next-video="$emit('next-video')"
      />

      <!-- 快进/快退指示器 -->
      <SeekingIndicator
        v-if="store.seekingState.active"
        :seeking-state="store.seekingState"
      />

      <!-- 音量调节指示器 -->
      <VolumeIndicator
        v-if="store.volumeState.showIndicator"
        :volume="store.volume"
      />

      <!-- 键盘帮助 -->
      <KeyboardHelp
        v-if="store.showKeyboardHelp"
        @close="toggleKeyboardHelp"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, watch, onMounted } from 'vue'
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
import useInitialTimeRestore from '../../composables/useInitialTimeRestore.js'

const props = defineProps({
  video: Object,
  initialTime: { type: Number, default: 0 },
  hasPrev: { type: Boolean, default: false },
  hasNext: { type: Boolean, default: false },
  externalError: { type: Object, default: null }
})

const emit = defineEmits(['play', 'pause', 'ended', 'fullscreenChange', 'timeupdate', 'error', 'prev-video', 'next-video'])

const {
  store,
  performanceState,
  videoCore,
  isHlsStream,
  isDashStream,
  isCanplay,
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

// 组件挂载时重置播放器状态
onMounted(() => {
  store.resetForNewVideo()
})

const isActiveBuffering = computed(() => {
  if (!(store.loading && store.loadingStage === 'buffering')) return false
  if (store.seekingVideo) return true
  if (store.hasStartedPlayback) return true
  return store.currentTime > 0
})

// 字幕集成
const videoElRef = computed(() => videoCore.value?.videoElement || null)
const { toggleSubtitles, setSubtitle, ensureSubtitlesOnMetadata, nextSubtitle } = useSubtitles({
  store,
  videoRef: videoElRef,
  props
})

// 元数据就绪时确保字幕加载
watch(() => store.canPlayVideo, (val) => {
  if (val) {
    try { ensureSubtitlesOnMetadata() } catch (e) {}
  }
})

// 从上次位置恢复
useInitialTimeRestore({
  store,
  videoCoreRef: videoCore,
  getInitialTime: () => Number(props.initialTime || 0),
  getVideoId: () => props.video?.id
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
  setPlaybackRate,
  updateAvailableQualities
} = useVideoControls(store, videoCore, props.video)

// 拖动进度条时的暂停/恢复
const onSeekStart = () => {
  if (!videoCore.value?.videoElement) return
  store.setIsDragging(true)
  store.updateSeekingState({ wasPlaying: store.playing })
  try { videoCore.value.videoElement.pause() } catch (e) {}
  if (videoCore.value.audioElement) {
    try { videoCore.value.audioElement.pause() } catch (e) {}
  }
}

const onSeekEnd = async () => {
  store.setIsDragging(false)
  if (store.seekingState.wasPlaying) {
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
const { handleKeyDown } = useKeyboardShortcuts(store, {
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
  nextSubtitle,
  toggleKeyboardHelp,
  handleEscapeKey: () => {
    if (store.showKeyboardHelp) {
      store.setShowKeyboardHelp(false)
    } else if (store.fullscreen) {
      toggleFullscreen()
    }
  },
  getDuration: () => store.duration,
  getCurrentTime: () => store.currentTime
})

defineExpose({ videoCore })

const onEnded = () => {
  try {
    emit('ended', {
      autoplay: store.autoplay,
      autoplayNext: store.autoplayNext,
      loop: store.loop
    })
  } catch (e) {
    emit('ended')
  }
}
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

.video-player-container:focus {
  outline: none;
}

.video-player-container:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.5);
}

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

.video-player-container:fullscreen .video-player,
.video-player-container:-webkit-full-screen .video-player,
.video-player-container:-moz-full-screen .video-player {
  width: 100% !important;
  height: 100% !important;
  object-fit: contain;
}

.loading-status-indicator {
  position: absolute;
  left: 1.5rem;
  bottom: 1.5rem;
  pointer-events: none;
  z-index: 25;
  transition: bottom 320ms cubic-bezier(0.7, 0, 0.84, 0);
}

.loading-status-indicator.with-controls {
  bottom: 5rem;
}

.loading-status-text {
  font-size: 0.875rem;
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}
</style>
