<template>
  <div class="video-wrapper bg-[#0f0f0f]">
    <div class="video-container" 
      @mouseenter="handleMouseEnter"
      @mouseleave="handleMouseLeave"
    >
      <div v-if="isLoading" class="yt-loading-spinner">
        <div class="yt-spinner">
          <svg class="yt-spinner__circle" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="45"/>
          </svg>
        </div>
      </div>

      <div class="video-click-layer" @click="togglePlay">
        <div class="play-state-indicator" v-if="showPlayIndicator">
          <Icon :icon="isPlaying ? 'material-symbols:pause' : 'material-symbols:play-arrow'" 
            class="indicator-icon" />
        </div>
      </div>

      <video
        ref="videoPlayer"
        class="video-player"
        :poster="video.thumbnail"
        :src="video.video_stream_url"
        @play="handleVideoPlay"
        @pause="handleVideoPause"
        @seeking="handleVideoSeeking"
        @canplay="handleVideoCanplay"
        @waiting="handleVideoWaiting"
        @timeupdate="handleVideoTimeupdate"
        @progress="handleVideoProgress"
        @error="handleVideoError"
      ></video>
      <audio
        ref="audioPlayer"
        :src="video.audio_stream_url"
        @seeking="handleAudioSeeking"
        @canplay="handleAudioCanplay"
        @error="handleAudioError"
      />
      
      <div class="hover-gradient"></div>
      
      <div class="video-controls" :class="{ 'controls-visible': isControlsVisible }">
        <div class="progress-container">
          <div class="preview-time-tooltip" :style="{ left: hoverPosition + '%' }" v-show="isHoveringProgress">
            {{ formatTime(previewTime) }}
          </div>
          
          <div class="progress-bar-container"
            @mousemove="handleProgressHover"
            @mouseleave="handleProgressLeave"
            @mousedown="handleProgressMouseDown"
          >
            <div class="progress-bar">
              <div class="progress-bar-loaded" :style="{ width: bufferedProgress + '%' }"></div>
              <div class="progress-bar-filled" :style="{ width: progress + '%' }">
                <div class="progress-dot"></div>
              </div>
            </div>
            <div class="progress-handle" :style="{ left: progress + '%' }" v-show="isHoveringProgress"></div>
          </div>
        </div>
        
        <div class="controls-main">
          <div class="controls-left">
            <button @click="togglePlay" class="control-btn">
              <Icon v-if="isPlaying" icon="material-symbols:pause" class="control-icon" />
              <Icon v-else icon="material-symbols:play-arrow" class="control-icon" />
            </button>
            
            <div class="volume-control group">
              <button @click="toggleMute" class="control-btn">
                <Icon :icon="volumeIcon" class="control-icon" />
              </button>
              
              <div class="volume-slider-container">
                <input 
                  type="range" 
                  min="0" 
                  max="100" 
                  v-model="volume" 
                  class="volume-range"
                >
              </div>
            </div>
            
            <div class="time-display">
              {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
            </div>
          </div>
          
          <div class="controls-right">
            <button class="control-btn">
              <Icon icon="material-symbols:subtitles" class="control-icon" />
            </button>
            
            <button class="control-btn">
              <Icon icon="material-symbols:settings" class="control-icon" />
            </button>
            
            <button @click="toggleFullscreen" class="control-btn">
              <Icon :icon="fullscreenIcon" class="control-icon" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, watch, ref, computed, onUnmounted } from 'vue';
import { Icon } from '@iconify/vue';
import useVideoOperations from "../composables/useVideoOperations";
import { formatTime } from "../utils/dateFormat";

const props = defineProps({
  video: Object,
  initialTime: {
    type: Number,
    default: 0
  }
});

const emit = defineEmits(['play', 'pause', 'ended', 'fullscreenChange', 'timeupdate']);

const videoPlayer = ref(null);
const audioPlayer = ref(null);
const {
  playVideo,
} = useVideoOperations();

const isPlaying = ref(false);
const volume = ref(100);
const isMuted = ref(false);
const currentTime = ref(0);
const duration = ref(0);
const isFullscreen = ref(false);
const bufferedProgress = ref(0);

const volumeIcon = computed(() => {
  if (isMuted.value || volume.value === 0) return 'material-symbols:volume-off';
  if (volume.value < 50) return 'material-symbols:volume-down';
  return 'material-symbols:volume-up';
});

const fullscreenIcon = computed(() => 
  isFullscreen.value ? 'material-symbols:fullscreen-exit' : 'material-symbols:fullscreen'
);

const isHoveringProgress = ref(false);
const hoverPosition = ref(0);
const previewTime = ref(0);

const isControlsVisible = ref(false);
let hideControlsTimer = null;

const showPlayIndicator = ref(false);
const isLoading = ref(false);
const isDragging = ref(false);
const previewSeekTime = ref(0);

const reconnectAttempts = ref(0);
const MAX_RECONNECT_ATTEMPTS = 3;
const RECONNECT_INTERVAL = 3000;

onMounted(async () => {
  if (!props.video?.stream_video_url) {
    await playVideo(props.video);
    if (props.video.stream_audio_url) {
      audioPlayer.value.src = props.video.stream_audio_url;
    }
  }
});

watch(() => props.video?.stream_video_url, async (newVideoUrl) => {
  if (newVideoUrl && videoPlayer.value) {
    console.debug('video url changed');
    videoPlayer.value.src = newVideoUrl;
  }
});

watch(() => props.video?.stream_audio_url, (newAudioUrl) => {
  if (audioPlayer.value && newAudioUrl) {
    audioPlayer.value.src = newAudioUrl;
  }
});

let firstCome = true;
let isVideoCanplay = false;
let isAudioCanplay = false;
let isAudioSeeking = false;
let isVideoSeeking = false;

const hasBeenActive = () => {
  return navigator.userActivation.hasBeenActive;
};

const isCanplay = () => {
  return isVideoCanplay && isAudioCanplay && hasBeenActive();
};

const isSeeking = () => {
  return isAudioSeeking || isVideoSeeking;
};

const handleVideoPlay = () => {
  firstCome = false;
  console.debug('video play', isVideoCanplay, isAudioCanplay);
  if (isCanplay()) {
    audioPlayer.value.currentTime = videoPlayer.value.currentTime;
    audioPlayer.value.play();
    console.debug(videoPlayer.value.currentTime, audioPlayer.value.currentTime);
  } else {
    videoPlayer.value.pause();
    audioPlayer.value.currentTime = videoPlayer.value.currentTime;
  }
  isPlaying.value = true;
};

const handleVideoPause = () => {
  console.debug('video pause');
  if (audioPlayer.value) {
    audioPlayer.value.pause();
  }
  if (!isSeeking()) {
    isPlaying.value = false;
  }
};

const handleVideoSeeking = () => {
  console.debug('video seeking');
  isLoading.value = true;
  audioPlayer.value.pause();
  videoPlayer.value.pause();
  isAudioCanplay = false;
  isVideoCanplay = false;
  isVideoSeeking = true;
};

const handleVideoCanplay = () => {
  if (videoPlayer.value) {
    duration.value = videoPlayer.value.duration;
  }
  isLoading.value = false;
  isVideoCanplay = true;
  isVideoSeeking = false;
  console.debug('video canplay', firstCome, isSeeking(), isCanplay());
  if (!isSeeking() && isCanplay()) {
    videoPlayer.value.play();
    audioPlayer.value.play();
  }
};

const handleVideoWaiting = () => {
  console.debug('video waiting');
  isLoading.value = true;
  if (audioPlayer.value) {
    audioPlayer.value.pause();
  }
};

const handleVideoTimeupdate = () => {
  if (videoPlayer.value) {
    currentTime.value = videoPlayer.value.currentTime;
    duration.value = videoPlayer.value.duration;
  }
};

const handleVideoProgress = () => {
  if ( videoPlayer.value && videoPlayer.value.buffered.length > 0) {
      bufferedProgress.value = (videoPlayer.value.buffered.end(0) / videoPlayer.value.duration) * 100;
  }
};

const handleAudioSeeking = () => {
  console.debug('audio seeking');
  isAudioSeeking = true;
};

const handleAudioCanplay = () => {
  isAudioCanplay = true;
  isAudioSeeking = false;
  console.debug('audio canplay', firstCome, isSeeking(), isCanplay());
  if (!isSeeking() && isCanplay()) {
    videoPlayer.value.play().then(() => {
        audioPlayer.value.play();
    });
  }
};

const togglePlay = () => {
  if (videoPlayer.value.paused) {
    reconnectAttempts.value = 0;
    videoPlayer.value.play().catch(handleVideoError);
  } else {
    videoPlayer.value.pause();
  }
  isPlaying.value = !videoPlayer.value.paused;
  
  showPlayIndicator.value = true;
  setTimeout(() => {
    showPlayIndicator.value = false;
  }, 500);
};

const toggleMute = () => {
  videoPlayer.value.muted = !videoPlayer.value.muted;
  audioPlayer.value.muted = videoPlayer.value.muted;
  isMuted.value = videoPlayer.value.muted;
};

const toggleFullscreen = async () => {
  if (!document.fullscreenElement) {
    await videoPlayer.value.parentElement.requestFullscreen();
    isFullscreen.value = true;
  } else {
    await document.exitFullscreen();
    isFullscreen.value = false;
  }
};

watch(volume, (newVolume) => {
  if (videoPlayer.value) {
    videoPlayer.value.volume = newVolume / 100;
    audioPlayer.value.volume = newVolume / 100;
  }
});

// 修改进度条处理逻辑
const handleProgressMouseDown = (e) => {
  console.debug('handleProgressMouseDown')
  e.preventDefault();
  isDragging.value = true;
  const rect = e.currentTarget.getBoundingClientRect();
  
  const updatePreview = (clientX) => {
    const position = (clientX - rect.left) / rect.width;
    previewSeekTime.value = duration.value * Math.min(Math.max(position, 0), 1);
    hoverPosition.value = position * 100;
  };

  updatePreview(e.clientX);

  const handleMouseMove = (e) => {
    console.debug('handleProgressMouseDown', isDragging.value)
    updatePreview(e.clientX);
  };

  const handleMouseUp = () => {
    isDragging.value = false;
    setVideoTime(previewSeekTime.value);
    
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  };

  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
};

// 修改进度显示逻辑
const progress = computed(() => {
  if (isDragging.value) {
    return (previewSeekTime.value / duration.value) * 100 || 0;
  }
  return (currentTime.value / duration.value) * 100 || 0;
});

// 修改时间显示逻辑
const handleProgressHover = (e) => {
  console.debug('handleProgressHover');
  isHoveringProgress.value = true;
  const rect = e.currentTarget.getBoundingClientRect();
  const position = ((e.clientX - rect.left) / rect.width) * 100;
  hoverPosition.value = Math.min(Math.max(position, 0), 100);
  previewTime.value = isDragging.value ? previewSeekTime.value : (duration.value * position) / 100;
};

const handleProgressLeave = () => {
  isHoveringProgress.value = false;
};

const setVideoTime = (time) => {
  videoPlayer.value.currentTime = time;
  audioPlayer.value.currentTime = time;
  currentTime.value = time;
};

const handleMouseEnter = () => {
  isControlsVisible.value = true;
  if (hideControlsTimer) {
    clearTimeout(hideControlsTimer);
  }
};

const handleMouseLeave = () => {
  hideControlsTimer = setTimeout(() => {
    if (!isHoveringProgress.value) {
      isControlsVisible.value = false;
    }
  }, 2000);
};

// 添加错误处理函数
const handleVideoError = () => {
  if (reconnectAttempts.value < MAX_RECONNECT_ATTEMPTS && !videoPlayer.value.paused) {
    isLoading.value = true;
    reconnectAttempts.value++;
    
    setTimeout(() => {
      videoPlayer.value.src = props.video.stream_video_url;
      videoPlayer.value.load();
      videoPlayer.value.play().catch(() => {
        handleVideoError();
      });
    }, RECONNECT_INTERVAL);
  } else {
    console.error('Video playback failed after maximum retries');
    isLoading.value = false;
  }
};

const handleAudioError = () => {
  if (reconnectAttempts.value < MAX_RECONNECT_ATTEMPTS && !audioPlayer.value.paused) {
    setTimeout(() => {
      audioPlayer.value.src = props.video.stream_audio_url;
      audioPlayer.value.load();
      audioPlayer.value.play().catch(() => {
        handleAudioError();
      });
    }, RECONNECT_INTERVAL);
  } else {
    console.error('Audio playback failed after maximum retries');
  }
};

onUnmounted(() => {
  if (hideControlsTimer) {
    clearTimeout(hideControlsTimer);
  }
  if (videoPlayer.value) {
    videoPlayer.value.removeEventListener('error', handleVideoError);
  }
  if (audioPlayer.value) {
    audioPlayer.value.removeEventListener('error', handleAudioError);
  }
});

defineExpose({
  videoPlayer
});

</script>

<style scoped>
.video-wrapper {
  @apply absolute top-0 left-0 w-full h-full flex items-center justify-center;
}

.video-container {
  @apply relative w-full h-full cursor-pointer;
}

.video-player {
  @apply w-full h-full object-contain;
}

.hover-gradient {
  @apply absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent 
    opacity-0 transition-opacity duration-300;
}

.video-container:hover .hover-gradient {
  @apply opacity-100;
}

.video-controls {
  @apply absolute bottom-0 left-0 right-0 px-4 pb-1
    opacity-0 transition-all duration-200 z-20
    flex flex-col;
}

.controls-visible {
  @apply opacity-100;
  transition-delay: 0s;
}

.video-controls:not(.controls-visible) {
  transition-delay: 2s;
}

.progress-container {
  @apply relative h-[5px] mb-0;
}

.preview-time-tooltip {
  @apply absolute bottom-8 bg-black/90 text-white px-2 py-1 rounded text-sm
    transform -translate-x-1/2 opacity-0 transition-opacity duration-200;
}

.progress-container:hover .preview-time-tooltip {
  @apply opacity-100;
}

.progress-bar-container {
  @apply absolute bottom-0 left-0 right-0 h-[5px] cursor-pointer z-30;
}

.progress-bar {
  @apply relative w-full h-[3px] bg-[#FFFFFF33]
    transition-all duration-200 overflow-hidden;
}

.progress-bar-loaded {
  @apply absolute top-0 left-0 h-full bg-[#FFFFFF26];
}

.progress-bar-filled {
  @apply absolute top-0 left-0 h-full bg-[#FF0000] flex items-center justify-end;
}

.progress-handle {
  @apply absolute bottom-1/2 w-[12px] h-[12px] rounded-full bg-[#FF0000]
    transform translate-y-1/2 -translate-x-1/2
    transition-opacity duration-200 opacity-0;
}

.progress-container:hover .progress-handle {
  @apply opacity-100;
}

.controls-main {
  @apply flex justify-between items-center;
}

.controls-left, .controls-right {
  @apply flex items-center gap-1;
}

.control-btn {
  @apply p-2 rounded-full hover:bg-white/20 transition-colors;
}

.control-icon {
  @apply text-white text-2xl;
}

.volume-control {
  @apply flex items-center relative;
}

.volume-slider-container {
  @apply w-0 overflow-hidden transition-all duration-200 origin-left;
}

.volume-control:hover .volume-slider-container {
  @apply w-20;
}

.volume-range {
  @apply w-full h-1 appearance-none bg-white/40 rounded-full cursor-pointer;
}

.volume-range::-webkit-slider-thumb {
  @apply appearance-none w-3 h-3 rounded-full bg-white cursor-pointer;
}

.time-display {
  @apply text-white text-sm ml-3 select-none;
}

.video-controls {
  font-family: "YouTube Noto", Roboto, Arial, sans-serif;
}

.progress-container:hover ~ .video-controls,
.video-controls:hover {
  @apply opacity-100;
  transition-delay: 0s;
}

.progress-dot {
  @apply w-[6px] h-[6px] rounded-full bg-[#FF0000] absolute right-0
    transform translate-x-1/2 opacity-0 transition-opacity duration-200;
}

.progress-container:hover .progress-dot {
  @apply opacity-100;
}

.progress-bar:hover .progress-dot {
  @apply w-[8px] h-[8px];
}

.play-state-indicator {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
    bg-black/50 rounded-full p-4 z-20
    animate-fade-out;
}

.indicator-icon {
  @apply text-white text-6xl;
}

@keyframes fade-out {
  from {
    opacity: 1;
  }
  to {
    opacity: 0;
  }
}

.animate-fade-out {
  animation: fade-out 0.5s ease-out forwards;
}

.video-click-layer {
  @apply absolute inset-0 z-10;
  bottom: 84px;
}

.yt-loading-spinner {
  @apply absolute inset-0 flex items-center justify-center z-20;
}

.yt-spinner {
  @apply w-12 h-12;
}

.yt-spinner__circle {
  @apply w-full h-full;
  fill: none;
  stroke: currentColor;
  stroke-width: 6;
  stroke-linecap: round;
  color: white;
  animation: yt-spinner 1.4s linear infinite;
}

.yt-spinner__circle circle {
  stroke-dasharray: 200;
  stroke-dashoffset: 800;
}

@keyframes yt-spinner {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

</style>
