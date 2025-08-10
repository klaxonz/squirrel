<template>
  <div class="video-core-container">
    <!-- 视频点击层 -->
    <div class="video-click-layer" @click="$emit('click')">
      <div class="play-state-indicator" v-if="playerState.ui.showPlayIndicator">
        <Icon 
          :icon="playerState.media.playing ? 'material-symbols:pause' : 'material-symbols:play-arrow'" 
          class="indicator-icon" 
        />
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
  isHlsStream: Boolean
})

const emit = defineEmits(['play', 'pause', 'timeupdate', 'error', 'click'])

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
  onError: (info) => emit('error', info)
})

// 视频事件处理
const handleVideoSeeking = () => {
  props.playerState.media.loading = true
  props.playerState.media.loadingStage = 'buffering'
  props.playerState.media.seeking.video = true
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
}

const handleVideoWaiting = () => {
  props.playerState.media.loading = true
  props.playerState.media.loadingStage = 'buffering'
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

onMounted(() => {
  initializeMediaSources()
})

defineExpose({
  videoElement,
  audioElement
})
</script>

<style scoped>
.video-core-container {
  @apply relative w-full h-full;
}

.video-click-layer {
  @apply absolute inset-0 z-10;
}

.video-player {
  @apply w-full h-full object-contain;
}

.play-state-indicator {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
    bg-black/50 rounded-full p-4 pointer-events-none;
}

.indicator-icon {
  @apply text-white text-4xl;
}

.hover-gradient {
  @apply absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent 
    opacity-100 transition-opacity duration-300;
}
</style>
