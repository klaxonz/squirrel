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
      :src="!isHlsStream && !isDashStream ? video.stream_video_url : undefined"
      preload="auto"
      crossorigin="anonymous"
      playsinline
      webkit-playsinline
      :muted="playerState.media.muted"
      :autoplay="playerState.media.autoplay"
      :loop="playerState.media.loop"
      @ended="$emit('ended')"
      @play="$emit('play')"
      @pause="$emit('pause')"
      @seeking="mediaEvents.handleVideoSeeking"
      @seeked="mediaEvents.handleVideoSeeked"
      @canplay="mediaEvents.handleVideoCanplay"
      @canplaythrough="mediaEvents.handleVideoCanplaythrough"
      @waiting="mediaEvents.handleVideoWaiting"
      @timeupdate="$emit('timeupdate', $event?.target?.currentTime)"
      @progress="mediaEvents.handleVideoProgress"
      @loadstart="mediaEvents.handleVideoLoadstart"
      @loadedmetadata="mediaEvents.handleVideoLoadedmetadata"
      @loadeddata="mediaEvents.handleVideoLoadeddata"
      @error="handleVideoElementError"
      @stalled="mediaEvents.handleVideoStalled"
      @suspend="mediaEvents.handleVideoSuspend"
      @abort="mediaEvents.handleVideoAbort"
    />

    <!-- 错误提示（非阻断，底部左侧） -->
    <LoadingSpinner
      v-if="errorState.show"
      :status-only="true"
      :loading-text="`${errorState.title} · ${errorState.message}${errorState.code ? `（${errorState.code}）` : ''}`"
    />

    <!-- 音频元素（仅非HLS/非DASH时） -->
    <audio
      v-if="!isHlsStream && !isDashStream && video.stream_audio_url"
      ref="audioElement"
      :src="video.stream_audio_url"
      :muted="playerState.media.muted"
      :autoplay="playerState.media.autoplay"
      preload="auto"
      @seeking="mediaEvents.handleAudioSeeking"
      @canplay="mediaEvents.handleAudioCanplay"
      @error="mediaEvents.handleAudioError"
    />

    <!-- 悬停渐变 -->
    <div
      class="hover-gradient"
      v-if="playerState.ui.controlsVisible && !playerState.media.subtitlesEnabled"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { Icon } from '@iconify/vue'
import LoadingSpinner from './LoadingSpinner.vue'
import useHlsPlayer from '../../composables/useHlsPlayer'
import useDashPlayer from '../../composables/useDashPlayer'
import useClickZones from '../../composables/useClickZones'
import useMediaError from '../../composables/useMediaError'
import useMediaEvents from '../../composables/useMediaEvents'

const props = defineProps({
  video: Object,
  playerState: Object,
  isHlsStream: Boolean,
  isDashStream: Boolean,
  onBandwidthSample: Function,
  onQualitiesUpdate: Function,
  helpUrl: String,
  externalError: Object
})

const emit = defineEmits(['play', 'pause', 'timeupdate', 'error', 'click', 'skip-forward', 'skip-backward', 'ended'])

const videoElement = ref(null)
const audioElement = ref(null)

// 使用点击区域逻辑
const {
  showLeftSkip,
  showRightSkip,
  handleLeftClick,
  handleRightClick,
  handleLeftDoubleClick,
  handleRightDoubleClick,
  cleanup: cleanupClickZones
} = useClickZones(emit)

// 使用错误处理逻辑
const {
  errorState,
  showInlineError,
  clearError,
  watchExternalError,
  cleanup: cleanupMediaError
} = useMediaError(emit, props)

// 监听外部错误
watchExternalError(props.playerState)

// 使用媒体事件处理逻辑
const mediaEvents = computed(() =>
  useMediaEvents(
    props.playerState,
    videoElement,
    audioElement,
    props.isHlsStream,
    clearError
  )
)

const handleVideoElementError = (evt) => {
  showInlineError(evt)
}

// HLS播放器管理
const {
  initializeHls,
  destroyHls,
  setQuality: setHlsQuality
} = useHlsPlayer({
  playerState: props.playerState,
  videoRef: videoElement,
  props,
  onProgress: (sample) => {
    try {
      if (!props.onBandwidthSample) return
      if (sample && typeof sample.loaded === 'number' && typeof sample.durationSec === 'number') {
        props.onBandwidthSample(sample.loaded, sample.durationSec)
      }
    } catch (_) {}
  },
  onError: (err) => showInlineError(err),
  onQualitiesUpdate: props.onQualitiesUpdate
})

// DASH 播放器管理
const {
  initializeDash,
  destroyDash,
  setQuality: setDashQuality
} = useDashPlayer({
  playerState: props.playerState,
  videoRef: videoElement,
  props,
  onProgress: (sample) => {
    try {
      const loaded = sample?.loaded || 0
      const durationSec = sample?.durationSec || 0
      if (loaded > 0 && durationSec > 0) {
        props.onBandwidthSample && props.onBandwidthSample(loaded, durationSec)
      }
    } catch (_) {}
  },
  onError: (err) => showInlineError(err),
  onQualitiesUpdate: props.onQualitiesUpdate
})

// 初始化媒体源
const initializeMediaSources = () => {
  const hasVideoUrl = !!props.video?.stream_video_url
  const hasMpd = !!props.video?.mpd_url || (hasVideoUrl && props.video.stream_video_url.endsWith('.mpd'))

  if (props.isHlsStream && hasVideoUrl) {
    try { destroyDash() } catch (_) {}
    initializeHls()
  } else if (hasMpd) {
    try { destroyHls() } catch (_) {}
    initializeDash()
  } else if (hasVideoUrl) {
    try { destroyHls() } catch (_) {}
    try { destroyDash() } catch (_) {}
    videoElement.value.src = props.video.stream_video_url
  } else {
    props.playerState.media.loading = true
    props.playerState.media.loadingStage = 'fetching'
  }

  // 非 HLS/DASH 才需要独立音频
  if (!props.isHlsStream && !props.isDashStream && props.video.stream_audio_url && audioElement.value) {
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

// 防抖定时器和去重标记
let initDebounceTimer = null
let lastInitializedUrl = null

// 监听视频URL和MPD URL变化
watch(
  () => [props.video?.stream_video_url, props.video?.mpd_url],
  ([newStreamUrl, newMpdUrl], [oldStreamUrl, oldMpdUrl]) => {
    const currentUrl = newMpdUrl || newStreamUrl || null
    
    if (currentUrl && currentUrl !== lastInitializedUrl &&
        ((newStreamUrl && newStreamUrl !== oldStreamUrl) || 
         (newMpdUrl && newMpdUrl !== oldMpdUrl))) {
      
      if (initDebounceTimer) {
        clearTimeout(initDebounceTimer)
      }
      
      initDebounceTimer = setTimeout(() => {
        lastInitializedUrl = currentUrl
        initializeMediaSources()
        initDebounceTimer = null
      }, 100)
    }
  }
)

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

// 监听清晰度变更
watch(() => props.playerState.media.currentQuality, (q) => {
  console.log('[Debug] Quality changed:', q, 'isHls=', props.isHlsStream, 'isDash=', props.isDashStream)
  try {
    if (props.isHlsStream) {
      setHlsQuality?.(q)
    } else if (props.isDashStream) {
      setDashQuality?.(q)
    }
  } catch (e) {
    console.warn('[Debug] setQuality failed', e)
  }
})

onMounted(() => {
  const currentUrl = props.video?.mpd_url || props.video?.stream_video_url || null
  lastInitializedUrl = currentUrl
  
  initializeMediaSources()

  if (videoElement.value) {
    videoElement.value.volume = props.playerState.media.volume / 100
    videoElement.value.muted = props.playerState.media.muted

    if (audioElement.value) {
      audioElement.value.volume = props.playerState.media.volume / 100
      audioElement.value.muted = props.playerState.media.muted
    }
  }
})

onUnmounted(() => {
  if (initDebounceTimer) {
    clearTimeout(initDebounceTimer)
    initDebounceTimer = null
  }
  lastInitializedUrl = null
  cleanupClickZones()
  cleanupMediaError()
  try { destroyHls() } catch (_) {}
  try { destroyDash() } catch (_) {}
})

defineExpose({
  videoElement,
  audioElement,
  reinitSources: () => {
    console.log('[Debug] 3.0 VideoPlayerCore.reinitSources invoked')
    initializeMediaSources()
  }
})
</script>

<style scoped>
.video-core-container {
  @apply relative w-full h-full;
  background: #000000;
}

.video-core-container::before {
  content: '';
  position: absolute;
  inset: 0;
  background: none;
  pointer-events: none;
  z-index: 1;
}

.video-core-container:hover .hover-gradient {
  @apply opacity-100;
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
  background: none;
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
</style>
