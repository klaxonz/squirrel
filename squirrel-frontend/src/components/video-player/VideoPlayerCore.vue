<template>
  <div class="video-core-container">
    <!-- 视频点击层 -->
    <div class="video-click-layer">
      <!-- 左侧双击区域 -->
      <div
        class="double-click-zone left-zone"
        @click="handleLeftClick"
        @dblclick="handleLeftDoubleClick"
      >
        <div class="skip-indicator left" v-if="showLeftSkip">
          <Icon icon="material-symbols:replay-10" class="skip-icon" />
        </div>
      </div>

      <!-- 中央单击区域 -->
      <div
        class="single-click-zone center-zone"
        @click="$emit('click')"
      >
        <div class="play-state-indicator" v-if="playerState.ui.showPlayIndicator">
          <Icon
            :icon="playerState.media.playing ? 'material-symbols:pause' : 'material-symbols:play-arrow'"
            class="indicator-icon"
          />
        </div>
      </div>

      <!-- 右侧双击区域 -->
      <div
        class="double-click-zone right-zone"
        @click="handleRightClick"
        @dblclick="handleRightDoubleClick"
      >
        <div class="skip-indicator right" v-if="showRightSkip">
          <Icon icon="material-symbols:forward-10" class="skip-icon" />
        </div>
      </div>
    </div>

    <!-- 主视频元素 -->
    <video
      ref="videoElement"
      class="video-player"
      :poster="video.thumbnail"
      :src="video.stream_video_url"
      preload="auto"
      crossorigin="anonymous"
      playsinline
      webkit-playsinline
      :muted="playerState.media.muted"
      :autoplay="playerState.media.autoplay"
      @play="$emit('play')"
      @pause="$emit('pause')"
      @seeking="handleVideoSeeking"
      @seeked="handleVideoSeeked"
      @canplay="handleVideoCanplay"
      @canplaythrough="handleVideoCanplaythrough"
      @waiting="handleVideoWaiting"
      @timeupdate="$emit('timeupdate')"
      @progress="handleVideoProgress"
      @loadstart="handleVideoLoadstart"
      @loadedmetadata="handleVideoLoadedmetadata"
      @loadeddata="handleVideoLoadeddata"
      @error="$emit('error', $event)"
      @stalled="handleVideoStalled"
      @suspend="handleVideoSuspend"
      @abort="handleVideoAbort"
    />

    <!-- 音频元素（非HLS时） -->
    <audio
      v-if="!isHlsStream && video.stream_audio_url"
      ref="audioElement"
      :src="video.stream_audio_url"
      :muted="playerState.media.muted"
      :autoplay="playerState.media.autoplay"
      preload="auto"
      @seeking="handleAudioSeeking"
      @canplay="handleAudioCanplay"
      @error="handleAudioError"
    />

    <!-- 悬停渐变 -->
    <div 
      class="hover-gradient" 
      v-if="playerState.ui.controlsVisible && !playerState.media.subtitlesEnabled"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import useHlsPlayer from '../../composables/useHlsPlayer'

const props = defineProps({
  video: Object,
  playerState: Object,
  isHlsStream: Boolean,
  onBandwidthSample: Function
})

const emit = defineEmits(['play', 'pause', 'timeupdate', 'error', 'click', 'skip-forward', 'skip-backward'])

// 双击跳跃状态
const showLeftSkip = ref(false)
const showRightSkip = ref(false)
let leftClickTimer = null
let rightClickTimer = null

const videoElement = ref(null)
const audioElement = ref(null)

// HLS播放器管理
const {
  initializeHls,
  destroyHls,
  reinitializeHls
} = useHlsPlayer({
  playerState: props.playerState,
  videoRef: videoElement,
  props,
  onProgress: (sample) => {
    try {
      console.log('Bandwidth sample:', sample)
      const loaded = sample?.loaded ?? 0
      const duration = sample?.durationSec ?? 0
      if (props.onBandwidthSample && loaded > 0 && duration > 0) {
        props.onBandwidthSample(loaded, duration)
      }
    } catch (e) {}
  },
  onError: (info) => emit('error', info)
})

// 视频事件处理
const handleVideoSeeking = () => {
  props.playerState.media.loading = true
  props.playerState.media.loadingStage = 'buffering'
  props.playerState.media.seeking.video = true
  // 在非HLS模式下，视频开始seek时暂停独立音频，避免继续播放造成不同步
  if (!props.isHlsStream && audioElement.value && !audioElement.value.paused) {
    try { audioElement.value.pause() } catch (e) {}
  }
}

const handleVideoSeeked = () => {
  props.playerState.media.loading = false
  props.playerState.media.loadingStage = 'ready'
  props.playerState.media.seeking.video = false
}

const handleVideoCanplay = () => {
  if (videoElement.value) {
    props.playerState.media.duration = videoElement.value.duration
  }
  props.playerState.media.loading = false
  props.playerState.media.loadingStage = 'ready'
  props.playerState.media.canPlay.video = true
  props.playerState.media.seeking.video = false
}

const handleVideoCanplaythrough = () => {
  props.playerState.media.loading = false
  props.playerState.media.loadingStage = 'ready'
  // 缓冲结束后，如需要，恢复音频播放
  if (!props.isHlsStream && audioElement.value && props.playerState.media.playing) {
    try { audioElement.value.play().catch(() => {}) } catch (e) {}
  }
}

const handleVideoWaiting = () => {
  props.playerState.media.loading = true
  props.playerState.media.loadingStage = 'buffering'
  // 缓冲时暂停独立音频，避免音画不同步（非HLS）
  if (!props.isHlsStream && audioElement.value && !audioElement.value.paused) {
    try { audioElement.value.pause() } catch (e) {}
  }
}

const handleVideoProgress = () => {
  if (videoElement.value && videoElement.value.buffered.length > 0) {
    const buffered = videoElement.value.buffered
    let bufferedEnd = 0
    
    for (let i = 0; i < buffered.length; i++) {
      if (buffered.start(i) <= props.playerState.media.currentTime &&
          buffered.end(i) >= props.playerState.media.currentTime) {
        bufferedEnd = buffered.end(i)
        break
      }
      if (buffered.end(i) > bufferedEnd) {
        bufferedEnd = buffered.end(i)
      }
    }
    
    props.playerState.media.bufferedProgress = 
      (bufferedEnd / props.playerState.media.duration) * 100
  }
}

const handleVideoLoadstart = () => {
  props.playerState.media.loading = true
  props.playerState.media.loadingStage = 'fetching'
}

const handleVideoLoadedmetadata = () => {
  props.playerState.media.loadingStage = 'buffering'
  if (videoElement.value) {
    props.playerState.media.duration = videoElement.value.duration
  }
}

const handleVideoLoadeddata = () => {
  props.playerState.media.loadingStage = 'ready'
  props.playerState.media.loading = false
}

const handleVideoStalled = () => {
  props.playerState.media.loading = true
  props.playerState.media.loadingStage = 'buffering'
}

const handleVideoSuspend = () => {
  // 网络空闲时暂停下载
}

const handleVideoAbort = () => {
  props.playerState.media.loading = false
}

// 音频事件处理
const handleAudioSeeking = () => {
  props.playerState.media.seeking.audio = true
}

const handleAudioCanplay = () => {
  props.playerState.media.canPlay.audio = true
  props.playerState.media.seeking.audio = false
}

const handleAudioError = () => {
  console.error('Audio playback error')
}

// 初始化媒体源
const initializeMediaSources = () => {
  if (props.video?.stream_video_url) {
    if (props.isHlsStream) {
      initializeHls()
    } else {
      videoElement.value.src = props.video.stream_video_url
    }
  }

  if (!props.isHlsStream && props.video.stream_audio_url && audioElement.value) {
    audioElement.value.src = props.video.stream_audio_url
  }

  // 确保媒体元素的音量和静音状态与playerState同步
  if (videoElement.value) {
    videoElement.value.volume = props.playerState.media.volume / 100
    videoElement.value.muted = props.playerState.media.muted
  }

  if (audioElement.value) {
    audioElement.value.volume = props.playerState.media.volume / 100
    audioElement.value.muted = props.playerState.media.muted
  }
}

// 监听视频URL变化
watch(() => props.video?.stream_video_url, (newUrl) => {
  if (newUrl) {
    initializeMediaSources()
  }
})

// 监听音量变化
watch(() => props.playerState.media.volume, (newVolume) => {
  if (videoElement.value) {
    videoElement.value.volume = newVolume / 100
    if (audioElement.value) {
      audioElement.value.volume = newVolume / 100
    }
  }
})

// 监听静音状态变化
watch(() => props.playerState.media.muted, (newMuted) => {
  if (videoElement.value) {
    videoElement.value.muted = newMuted
    if (audioElement.value) {
      audioElement.value.muted = newMuted
    }
  }
})

// 双击处理函数
const handleLeftClick = () => {
  // 单击延迟处理，如果在延迟期间发生双击则取消单击
  if (leftClickTimer) {
    clearTimeout(leftClickTimer)
    leftClickTimer = null
    return
  }

  leftClickTimer = setTimeout(() => {
    // 这里可以添加左侧单击逻辑，目前不做任何操作
    leftClickTimer = null
  }, 300)
}

const handleRightClick = () => {
  if (rightClickTimer) {
    clearTimeout(rightClickTimer)
    rightClickTimer = null
    return
  }

  rightClickTimer = setTimeout(() => {
    // 这里可以添加右侧单击逻辑，目前不做任何操作
    rightClickTimer = null
  }, 300)
}

const handleLeftDoubleClick = () => {
  if (leftClickTimer) {
    clearTimeout(leftClickTimer)
    leftClickTimer = null
  }

  showLeftSkip.value = true
  emit('skip-backward')

  setTimeout(() => {
    showLeftSkip.value = false
  }, 500)
}

const handleRightDoubleClick = () => {
  if (rightClickTimer) {
    clearTimeout(rightClickTimer)
    rightClickTimer = null
  }

  showRightSkip.value = true
  emit('skip-forward')

  setTimeout(() => {
    showRightSkip.value = false
  }, 500)
}

onMounted(() => {
  initializeMediaSources()

  // 确保初始音量和静音状态正确设置
  if (videoElement.value) {
    videoElement.value.volume = props.playerState.media.volume / 100
    videoElement.value.muted = props.playerState.media.muted

    if (audioElement.value) {
      audioElement.value.volume = props.playerState.media.volume / 100
      audioElement.value.muted = props.playerState.media.muted
    }
  }
})

defineExpose({
  videoElement,
  audioElement
})
</script>

<style scoped>
.video-core-container {
  @apply relative w-full h-full;
  background: #000000;
}

.video-click-layer {
  @apply absolute inset-0 z-10 flex;
}

.double-click-zone {
  @apply relative flex-1 cursor-pointer
    flex items-center justify-center;
}

.single-click-zone {
  @apply relative flex-1 cursor-pointer
    flex items-center justify-center;
}

.left-zone {
  @apply justify-start pl-12;
}

.right-zone {
  @apply justify-end pr-12;
}

.skip-indicator {
  @apply absolute inset-0 flex items-center justify-center
    pointer-events-none;
}

.skip-indicator.left {
  @apply justify-start pl-12;
}

.skip-indicator.right {
  @apply justify-end pr-12;
}

.skip-icon {
  @apply text-white text-6xl;
  filter: drop-shadow(0 4px 12px rgba(0,0,0,0.6));
  animation: skipIconPulse 0.5s ease-out;
}

.video-player {
  @apply w-full h-full object-contain;
}

.play-state-indicator {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
    rounded-full p-3 pointer-events-none;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(8px);
  border: 2px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
  animation: playIndicatorPulse 0.5s ease-out;
}

.indicator-icon {
  @apply text-white;
  font-size: 28px;
  filter: drop-shadow(0 2px 8px rgba(0,0,0,0.5));
}

.hover-gradient {
  @apply absolute inset-0 opacity-0 transition-opacity duration-300 pointer-events-none;
  background: linear-gradient(
    to top,
    rgba(0,0,0,0.7) 0%,
    rgba(0,0,0,0.3) 30%,
    transparent 60%
  );
}

.video-core-container:hover .hover-gradient {
  @apply opacity-100;
}

@keyframes playIndicatorPulse {
  0% {
    transform: translate(-50%, -50%) scale(0.8);
    opacity: 0;
  }
  50% {
    transform: translate(-50%, -50%) scale(1.1);
    opacity: 1;
  }
  100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 1;
  }
}

@keyframes skipIconPulse {
  0% {
    transform: scale(0.8);
    opacity: 0;
  }
  50% {
    transform: scale(1.2);
    opacity: 1;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

/* YouTube风格的视频容器 */
.video-core-container::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at center, transparent 0%, rgba(0,0,0,0.1) 100%);
  pointer-events: none;
  z-index: 1;
}
</style>
