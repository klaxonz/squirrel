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
        <div class="play-state-indicator" v-if="store.showPlayIndicator">
          <Icon
            :icon="store.playing ? 'material-symbols:pause' : 'material-symbols:play-arrow'"
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
      :muted="store.muted"
      :autoplay="store.autoplay"
      :loop="store.loop"
      @ended="$emit('ended')"
      @play="$emit('play')"
      @pause="$emit('pause')"
      @seeking="handleVideoSeeking"
      @seeked="handleVideoSeeked"
      @canplay="handleVideoCanplay"
      @canplaythrough="handleVideoCanplaythrough"
      @waiting="handleVideoWaiting"
      @timeupdate="$emit('timeupdate', $event?.target?.currentTime)"
      @progress="handleVideoProgress"
      @loadstart="handleVideoLoadstart"
      @loadedmetadata="handleVideoLoadedmetadata"
      @loadeddata="handleVideoLoadeddata"
      @error="handleVideoElementError"
      @stalled="handleVideoStalled"
      @suspend="handleVideoSuspend"
      @abort="handleVideoAbort"
    />

    <!-- 错误提示 -->
    <LoadingSpinner
      v-if="errorState.show"
      :status-only="true"
      :loading-text="`${errorState.title} · ${errorState.message}${errorState.code ? `（${errorState.code}）` : ''}`"
    />

    <!-- 音频元素 -->
    <audio
      v-if="!isHlsStream && !isDashStream && video.stream_audio_url"
      ref="audioElement"
      :src="video.stream_audio_url"
      :muted="store.muted"
      :autoplay="store.autoplay"
      preload="auto"
      @seeking="handleAudioSeeking"
      @canplay="handleAudioCanplay"
      @error="handleAudioError"
    />

    <!-- 悬停渐变 -->
    <div
      class="hover-gradient"
      v-if="store.controlsVisible && !store.subtitlesEnabled"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { Icon } from '@iconify/vue'
import LoadingSpinner from './LoadingSpinner.vue'
import { usePlayerStore } from '../../stores/playerStore'
import useHlsPlayer from '../../composables/useHlsPlayer'
import useDashPlayer from '../../composables/useDashPlayer'
import useClickZones from '../../composables/useClickZones'

const props = defineProps({
  video: Object,
  isHlsStream: Boolean,
  isDashStream: Boolean,
  onBandwidthSample: Function,
  onQualitiesUpdate: Function,
  externalError: Object
})

const emit = defineEmits(['play', 'pause', 'timeupdate', 'error', 'click', 'skip-forward', 'skip-backward', 'ended'])

const store = usePlayerStore()
const videoElement = ref(null)
const audioElement = ref(null)

// 点击区域逻辑
const {
  showLeftSkip,
  showRightSkip,
  handleLeftClick,
  handleRightClick,
  handleLeftDoubleClick,
  handleRightDoubleClick,
  cleanup: cleanupClickZones
} = useClickZones(emit)

// 错误状态
const errorState = ref({ show: false, title: '', message: '', code: '' })
let hideTimer = null

const scheduleAutoHide = () => {
  if (hideTimer) clearTimeout(hideTimer)
  hideTimer = setTimeout(() => { errorState.value.show = false }, 6000)
}

const mapErrorToUi = (err) => {
  const e = err || {}
  const type = e.type || (e.name || '').toLowerCase()
  if (type === 'network') return { title: '网络连接错误', message: '无法连接到服务器', code: e.code || 'NETWORK' }
  if (type === 'media') return { title: '媒体播放错误', message: '视频无法播放', code: e.code || 'MEDIA' }
  if (type === 'fatal') return { title: '播放失败', message: '发生致命错误', code: e.code || 'FATAL' }
  const mediaErr = e?.target?.error || e.error || {}
  switch (mediaErr.code) {
    case 1: return { title: '已中止', message: '播放被中止', code: 'MEDIA_ERR_ABORTED' }
    case 2: return { title: '网络错误', message: '网络连接异常', code: 'MEDIA_ERR_NETWORK' }
    case 3: return { title: '解码错误', message: '媒体解码失败', code: 'MEDIA_ERR_DECODE' }
    case 4: return { title: '不支持的资源', message: '媒体资源不受支持', code: 'MEDIA_ERR_SRC_NOT_SUPPORTED' }
    default: return { title: '播放出现问题', message: '请稍后重试', code: e.code || 'UNKNOWN' }
  }
}

const showInlineError = (err) => {
  const ui = mapErrorToUi(err)
  errorState.value = { show: true, ...ui }
  scheduleAutoHide()
  emit('error', err)
}

const clearError = () => {
  errorState.value.show = false
  if (hideTimer) { clearTimeout(hideTimer); hideTimer = null }
}

// 外部错误监听
watch(() => props.externalError, (info) => {
  if (!info) return
  const CODES = {
    EXTRACT_FAILED: { title: '播放失败', message: '播放链接提取失败' },
    NO_STREAM_URL: { title: '无法播放', message: '没有获取到播放链接' },
    URL_FETCH_TIMEOUT: { title: '获取超时', message: '获取播放链接超时' }
  }
  const mapped = CODES[info.code] || { title: info.title || '播放失败', message: info.message || '' }
  errorState.value = { show: true, ...mapped, code: info.code || '' }
  scheduleAutoHide()
  store.setPlaying(false)
  store.setLoading(false, 'idle')
  store.setCanPlay('video', false)
  store.setCanPlay('audio', false)
})

const handleVideoElementError = (evt) => showInlineError(evt)

// 视频事件处理
const handleVideoSeeking = () => {
  store.setLoading(true, 'buffering')
  store.setSeeking('video', true)
  if (!props.isHlsStream && audioElement.value && !audioElement.value.paused) {
    try { audioElement.value.pause() } catch (e) {}
  }
}

const handleVideoSeeked = () => {
  store.setLoading(false, 'ready')
  store.setSeeking('video', false)
}

const handleVideoCanplay = () => {
  if (videoElement.value) store.setDuration(videoElement.value.duration)
  store.setLoading(false, 'ready')
  store.setCanPlay('video', true)
  store.setSeeking('video', false)
  clearError()
}

const handleVideoCanplaythrough = () => {
  store.setLoading(false, 'ready')
  if (!props.isHlsStream && audioElement.value && store.playing) {
    try { audioElement.value.play().catch(() => {}) } catch (e) {}
  }
}

const handleVideoWaiting = () => {
  store.setLoading(true, 'buffering')
  if (!props.isHlsStream && audioElement.value && !audioElement.value.paused) {
    try { audioElement.value.pause() } catch (e) {}
  }
}

const handleVideoProgress = () => {
  if (videoElement.value && videoElement.value.buffered.length > 0) {
    const buffered = videoElement.value.buffered
    let bufferedEnd = 0
    for (let i = 0; i < buffered.length; i++) {
      if (buffered.start(i) <= store.currentTime && buffered.end(i) >= store.currentTime) {
        bufferedEnd = buffered.end(i)
        break
      }
      if (buffered.end(i) > bufferedEnd) bufferedEnd = buffered.end(i)
    }
    store.setBufferedProgress((bufferedEnd / store.duration) * 100)
  }
}

const handleVideoLoadstart = () => store.setLoading(true, 'fetching')
const handleVideoLoadedmetadata = () => {
  store.setLoading(true, store.hasStartedPlayback ? 'buffering' : 'fetching')
  if (videoElement.value) store.setDuration(videoElement.value.duration)
}
const handleVideoLoadeddata = () => store.setLoading(false, 'ready')
const handleVideoStalled = () => store.setLoading(true, 'buffering')
const handleVideoSuspend = () => {}
const handleVideoAbort = () => store.setLoading(false)

// 音频事件
const handleAudioSeeking = () => store.setSeeking('audio', true)
const handleAudioCanplay = () => {
  store.setCanPlay('audio', true)
  store.setSeeking('audio', false)
}
const handleAudioError = () => console.error('Audio playback error')

// HLS播放器
const {
  initializeHls,
  destroyHls,
  setQuality: setHlsQuality
} = useHlsPlayer({
  store,
  videoRef: videoElement,
  props,
  onProgress: (sample) => {
    if (props.onBandwidthSample && sample?.loaded && sample?.durationSec) {
      props.onBandwidthSample(sample.loaded, sample.durationSec)
    }
  },
  onError: showInlineError,
  onQualitiesUpdate: props.onQualitiesUpdate
})

// DASH播放器
const {
  initializeDash,
  destroyDash,
  setQuality: setDashQuality
} = useDashPlayer({
  store,
  videoRef: videoElement,
  props,
  onProgress: (sample) => {
    if (props.onBandwidthSample && sample?.loaded && sample?.durationSec) {
      props.onBandwidthSample(sample.loaded, sample.durationSec)
    }
  },
  onError: showInlineError,
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
    store.setLoading(true, 'fetching')
  }

  if (!props.isHlsStream && !props.isDashStream && props.video.stream_audio_url && audioElement.value) {
    audioElement.value.src = props.video.stream_audio_url
  }

  if (videoElement.value) {
    videoElement.value.volume = store.volume / 100
    videoElement.value.muted = store.muted
  }
  if (audioElement.value) {
    audioElement.value.volume = store.volume / 100
    audioElement.value.muted = store.muted
  }
}

let initDebounceTimer = null
let lastInitializedUrl = null

watch(
  () => [props.video?.stream_video_url, props.video?.mpd_url],
  ([newStreamUrl, newMpdUrl], [oldStreamUrl, oldMpdUrl]) => {
    const currentUrl = newMpdUrl || newStreamUrl || null
    if (currentUrl && currentUrl !== lastInitializedUrl &&
        ((newStreamUrl && newStreamUrl !== oldStreamUrl) || (newMpdUrl && newMpdUrl !== oldMpdUrl))) {
      if (initDebounceTimer) clearTimeout(initDebounceTimer)
      initDebounceTimer = setTimeout(() => {
        lastInitializedUrl = currentUrl
        initializeMediaSources()
        initDebounceTimer = null
      }, 100)
    }
  }
)

watch(() => store.volume, (newVolume) => {
  if (videoElement.value) videoElement.value.volume = newVolume / 100
  if (audioElement.value) audioElement.value.volume = newVolume / 100
})

watch(() => store.muted, (newMuted) => {
  if (videoElement.value) videoElement.value.muted = newMuted
  if (audioElement.value) audioElement.value.muted = newMuted
})

watch(() => store.currentQuality, (q) => {
  console.log('[Debug] Quality changed:', q)
  try {
    if (props.isHlsStream) setHlsQuality?.(q)
    else if (props.isDashStream) setDashQuality?.(q)
  } catch (e) { console.warn('[Debug] setQuality failed', e) }
})

onMounted(() => {
  lastInitializedUrl = props.video?.mpd_url || props.video?.stream_video_url || null
  initializeMediaSources()
  if (videoElement.value) {
    videoElement.value.volume = store.volume / 100
    videoElement.value.muted = store.muted
  }
  if (audioElement.value) {
    audioElement.value.volume = store.volume / 100
    audioElement.value.muted = store.muted
  }
})

onUnmounted(() => {
  if (initDebounceTimer) { clearTimeout(initDebounceTimer); initDebounceTimer = null }
  if (hideTimer) { clearTimeout(hideTimer); hideTimer = null }
  lastInitializedUrl = null
  cleanupClickZones()
  try { destroyHls() } catch (_) {}
  try { destroyDash() } catch (_) {}
})

defineExpose({
  videoElement,
  audioElement,
  reinitSources: () => { console.log('[Debug] VideoPlayerCore.reinitSources'); initializeMediaSources() }
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
  @apply relative flex-1 cursor-pointer flex items-center justify-center;
}

.single-click-zone {
  @apply relative flex-1 cursor-pointer flex items-center justify-center;
}

.left-zone { @apply justify-start pl-12; }
.right-zone { @apply justify-end pr-12; }

.skip-indicator {
  @apply absolute inset-0 flex items-center justify-center pointer-events-none;
}
.skip-indicator.left { @apply justify-start pl-12; }
.skip-indicator.right { @apply justify-end pr-12; }

.skip-icon {
  @apply text-white text-6xl;
  filter: drop-shadow(0 4px 12px rgba(0,0,0,0.6));
  animation: skipIconPulse 0.5s ease-out;
}

.video-player { @apply w-full h-full object-contain; }

.play-state-indicator {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 rounded-full p-3 pointer-events-none;
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
  0% { transform: translate(-50%, -50%) scale(0.8); opacity: 0; }
  50% { transform: translate(-50%, -50%) scale(1.1); opacity: 1; }
  100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
}

@keyframes skipIconPulse {
  0% { transform: scale(0.8); opacity: 0; }
  50% { transform: scale(1.2); opacity: 1; }
  100% { transform: scale(1); opacity: 1; }
}
</style>
