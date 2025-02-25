<template>
  <div class="video-wrapper bg-[#0f0f0f]">
    <div class="video-container" 
      @mouseenter="handleMouseEnter"
      @mouseleave="handleMouseLeave"
      @dblclick="togglePlay"
      @touchstart="handleTouchStart"
      @touchend="handleTouchEnd"
    >
      <div v-if="playerState.media.loading" class="yt-loading-spinner">
        <div class="yt-spinner">
          <svg class="yt-spinner__circle" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="45"/>
          </svg>
        </div>
      </div>

      <div class="video-click-layer" @click="togglePlay">
        <div class="play-state-indicator" v-if="playerState.ui.showPlayIndicator">
          <Icon :icon="playerState.media.playing ? 'material-symbols:pause' : 'material-symbols:play-arrow'" 
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
        v-if="!isHlsStream"
        ref="audioPlayer"
        :src="video.audio_stream_url"
        @seeking="handleAudioSeeking"
        @canplay="handleAudioCanplay"
        @error="handleAudioError"
      />
      
      <div class="hover-gradient"></div>
      
      <div class="video-controls" :class="{ 'controls-visible': playerState.ui.controlsVisible }">
        <div class="progress-container">
          <div class="preview-time-tooltip" :style="{ left: playerState.ui.hoverPosition + '%' }" v-show="playerState.ui.hoveringProgress">
            {{ formatTime(playerState.ui.previewTime) }}
          </div>
          
          <div class="progress-bar-container"
            @mousemove="handleProgressHover"
            @mouseleave="handleProgressLeave"
            @mousedown="handleProgressMouseDown"
            @touchstart="handleProgressTouchStart"
            @touchmove="handleProgressTouchMove"
            @touchend="handleProgressTouchEnd"
          >
            <div class="progress-bar">
              <div class="progress-bar-loaded" :style="{ width: playerState.media.bufferedProgress + '%' }"></div>
              <div class="progress-bar-filled" :style="{ width: progress + '%' }">
                <div class="progress-dot"></div>
              </div>
            </div>
            <div class="progress-handle" :style="{ left: progress + '%' }" v-show="playerState.ui.hoveringProgress"></div>
          </div>
        </div>
        
        <div class="controls-main">
          <div class="controls-left">
            <button @click="togglePlay" class="control-btn">
              <Icon v-if="playerState.media.playing" icon="material-symbols:pause" class="control-icon" />
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
                  v-model="playerState.media.volume" 
                  class="volume-range"
                >
              </div>
            </div>
            
            <div class="time-display">
              {{ formatTime(playerState.media.currentTime) }} / {{ formatTime(playerState.media.duration) }}
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
import { onMounted, watch, ref, computed, onUnmounted, reactive } from 'vue';
import { Icon } from '@iconify/vue';
import useVideoOperations from "../composables/useVideoOperations";
import { formatTime } from "../utils/dateFormat";
import Hls from 'hls.js';

const props = defineProps({
  video: Object,
  initialTime: {
    type: Number,
    default: 0
  }
});

const emit = defineEmits(['play', 'pause', 'ended', 'fullscreenChange', 'timeupdate']);

// DOM 引用
const videoPlayer = ref(null);
const audioPlayer = ref(null);
const {
  playVideo,
} = useVideoOperations();

// 统一状态对象
const playerState = reactive({
  // 媒体状态
  media: {
    playing: false,
    canPlay: {
      video: false,
      audio: false
    },
    seeking: {
      video: false,
      audio: false
    },
    loading: false,
    volume: 100,
    muted: false,
    currentTime: 0,
    duration: 0,
    bufferedProgress: 0
  },
  // UI状态
  ui: {
    controlsVisible: false,
    fullscreen: false,
    hoveringProgress: false,
    hoverPosition: 0,
    previewTime: 0,
    showPlayIndicator: false,
    isDragging: false,
    previewSeekTime: 0
  },
  // 网络状态
  network: {
    reconnectAttempts: 0,
    firstInteraction: true
  }
});

// HLS 实例
const hls = ref(null);

// 计算属性
const isHlsStream = computed(() => 
  props.video?.stream_video_url?.includes('.m3u8')
);

const isCanplay = computed(() => 
  playerState.media.canPlay.video && 
  (isHlsStream.value || playerState.media.canPlay.audio)
);

const isSeeking = computed(() => 
  playerState.media.seeking.video || playerState.media.seeking.audio
);

const volumeIcon = computed(() => {
  if (playerState.media.muted || playerState.media.volume === 0) 
    return 'material-symbols:volume-off';
  if (playerState.media.volume < 50) 
    return 'material-symbols:volume-down';
  return 'material-symbols:volume-up';
});

const fullscreenIcon = computed(() => 
  playerState.ui.fullscreen ? 'material-symbols:fullscreen-exit' : 'material-symbols:fullscreen'
);

const progress = computed(() => {
  if (playerState.ui.isDragging) {
    return (playerState.ui.previewSeekTime / playerState.media.duration) * 100 || 0;
  }
  return (playerState.media.currentTime / playerState.media.duration) * 100 || 0;
});

// 常量
const MAX_RECONNECT_ATTEMPTS = 3;
const RECONNECT_INTERVAL = 3000;

// 触摸状态
const lastTap = ref(0);
const touchStartTime = ref(0);

// 计时器
let hideControlsTimer = null;

// 初始化
onMounted(async () => {
  if (!props.video?.stream_video_url) {
    await playVideo(props.video);
  }
  
  initializeMediaSources();
  screen.orientation?.addEventListener('change', handleOrientationChange);
});

// 初始化媒体源
const initializeMediaSources = () => {
  if (props.video?.stream_video_url) {
    if (isHlsStream.value) {
      initializeHlsStream();
    } else {
      videoPlayer.value.src = props.video.stream_video_url;
    }
  }

  if (!isHlsStream.value && props.video.stream_audio_url) {
    audioPlayer.value.src = props.video.stream_audio_url;
  }
};

// 初始化HLS播放
const initializeHlsStream = () => {
  if (Hls.isSupported()) {
    hls.value = new Hls();
    hls.value.attachMedia(videoPlayer.value);
    hls.value.on(Hls.Events.MEDIA_ATTACHED, () => {
      hls.value.loadSource(props.video.stream_video_url);
    });
    
    hls.value.on(Hls.Events.ERROR, (event, data) => {
      handleHlsError(data);
    });
  } else if (videoPlayer.value.canPlayType('application/vnd.apple.mpegurl')) {
    // Safari原生支持
    videoPlayer.value.src = props.video.stream_video_url;
  }
};

// URL变更监听
watch(() => props.video?.stream_video_url, async (newVideoUrl) => {
  if (newVideoUrl && videoPlayer.value) {
    console.debug('video url changed');
    if (isHlsStream.value) {
      initializeHlsStream();
    } else {
      videoPlayer.value.src = newVideoUrl;
    }
  }
});

watch(() => props.video?.stream_audio_url, (newAudioUrl) => {
  if (!isHlsStream.value && audioPlayer.value && newAudioUrl) {
    audioPlayer.value.src = newAudioUrl;
  }
});

// 音量监听
watch(() => playerState.media.volume, (newVolume) => {
  if (videoPlayer.value) {
    videoPlayer.value.volume = newVolume / 100;
    if (audioPlayer.value) {
      audioPlayer.value.volume = newVolume / 100;
    }
  }
});

// 视频事件处理
const handleVideoPlay = () => {
  playerState.network.firstInteraction = false;
  console.debug('video play', playerState.media.canPlay.video, playerState.media.canPlay.audio);
  
  if (isCanplay.value) {
    if (!isHlsStream.value && audioPlayer.value) {
      audioPlayer.value.currentTime = videoPlayer.value.currentTime;
      audioPlayer.value.play();
    }
    playerState.media.playing = true;
  } else {
    videoPlayer.value.pause();
    if (!isHlsStream.value && audioPlayer.value) {
      audioPlayer.value.currentTime = videoPlayer.value.currentTime;
    }
  }
};

const handleVideoPause = () => {
  console.debug('video pause');
  if (!isHlsStream.value && audioPlayer.value) {
    audioPlayer.value.pause();
  }
  if (!isSeeking.value) {
    playerState.media.playing = false;
  }
};

const handleVideoSeeking = () => {
  console.debug('video seeking');
  playerState.media.loading = true;
  if (!isHlsStream.value && audioPlayer.value) {
    audioPlayer.value.pause();
  }
  videoPlayer.value.pause();
  playerState.media.canPlay.audio = false;
  playerState.media.canPlay.video = false;
  playerState.media.seeking.video = true;
};

const handleVideoCanplay = () => {
  if (videoPlayer.value) {
    playerState.media.duration = videoPlayer.value.duration;
  }
  playerState.media.loading = false;
  playerState.media.canPlay.video = true;
  playerState.media.seeking.video = false;
  
  console.debug('video canplay', playerState.network.firstInteraction, isSeeking.value, isCanplay.value);
  
  if (!isSeeking.value && isCanplay.value) {
    videoPlayer.value.play();
    if (!isHlsStream.value && audioPlayer.value) {
      audioPlayer.value.play();
    }
  }
};

const handleVideoWaiting = () => {
  console.debug('video waiting');
  playerState.media.loading = true;
  if (!isHlsStream.value && audioPlayer.value) {
    audioPlayer.value.pause();
  }
};

const handleVideoTimeupdate = () => {
  if (videoPlayer.value) {
    playerState.media.currentTime = videoPlayer.value.currentTime;
    playerState.media.duration = videoPlayer.value.duration;
  }
};

const handleVideoProgress = () => {
  if (videoPlayer.value && videoPlayer.value.buffered.length > 0) {
    playerState.media.bufferedProgress = 
      (videoPlayer.value.buffered.end(0) / videoPlayer.value.duration) * 100;
  }
};

// 音频事件处理
const handleAudioSeeking = () => {
  console.debug('audio seeking');
  playerState.media.seeking.audio = true;
};

const handleAudioCanplay = () => {
  playerState.media.canPlay.audio = true;
  playerState.media.seeking.audio = false;
  
  console.debug('audio canplay', playerState.network.firstInteraction, isSeeking.value, isCanplay.value);
  
  if (!isSeeking.value && isCanplay.value) {
    videoPlayer.value.play().then(() => {
      if (!isHlsStream.value && audioPlayer.value) {
        audioPlayer.value.play();
      }
    });
  }
};

// 用户交互
const togglePlay = () => {
  if (videoPlayer.value.paused) {
    playerState.network.reconnectAttempts = 0; // 重置重连计数
    videoPlayer.value.play().catch(handleVideoError);
    if (!isHlsStream.value && audioPlayer.value) {
      audioPlayer.value.play();
    }
  } else {
    videoPlayer.value.pause();
    if (!isHlsStream.value && audioPlayer.value) {
      audioPlayer.value.pause();
    }
  }
  playerState.media.playing = !videoPlayer.value.paused;
  
  playerState.ui.showPlayIndicator = true;
  setTimeout(() => {
    playerState.ui.showPlayIndicator = false;
  }, 500);
};

const toggleMute = () => {
  videoPlayer.value.muted = !videoPlayer.value.muted;
  if (!isHlsStream.value && audioPlayer.value) {
    audioPlayer.value.muted = videoPlayer.value.muted;
  }
  playerState.media.muted = videoPlayer.value.muted;
};

const toggleFullscreen = async () => {
  if (document.fullscreenElement) {
    await document.exitFullscreen();
  } else {
    const elem = videoPlayer.value.parentElement;
    if (elem.requestFullscreen) {
      await elem.requestFullscreen();
    } else if (elem.webkitRequestFullscreen) { /* Safari */
      await elem.webkitRequestFullscreen();
    } else if (elem.mozRequestFullScreen) { /* Firefox */
      await elem.mozRequestFullScreen();
    }
  }
  playerState.ui.fullscreen = !document.fullscreenElement;
};

// 进度条交互
const handleProgressMouseDown = (e) => {
  e.preventDefault();
  playerState.ui.isDragging = true;
  const rect = e.currentTarget.getBoundingClientRect();
  
  const updatePreview = (clientX) => {
    const position = (clientX - rect.left) / rect.width;
    playerState.ui.previewSeekTime = 
      playerState.media.duration * Math.min(Math.max(position, 0), 1);
    playerState.ui.hoverPosition = position * 100;
  };

  updatePreview(e.clientX);

  const handleMouseMove = (e) => {
    if (!playerState.ui.isDragging) return;
    updatePreview(e.clientX);
  };

  const handleMouseUp = () => {
    playerState.ui.isDragging = false;
    setVideoTime(playerState.ui.previewSeekTime);
    
    // 清理事件监听
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  };

  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
};

const handleProgressHover = (e) => {
  playerState.ui.hoveringProgress = true;
  const rect = e.currentTarget.getBoundingClientRect();
  const position = ((e.clientX - rect.left) / rect.width) * 100;
  playerState.ui.hoverPosition = Math.min(Math.max(position, 0), 100);
  playerState.ui.previewTime = 
    playerState.ui.isDragging 
      ? playerState.ui.previewSeekTime 
      : (playerState.media.duration * position) / 100;
};

const handleProgressLeave = () => {
  playerState.ui.hoveringProgress = false;
};

// 设置视频时间
const setVideoTime = (time) => {
  videoPlayer.value.currentTime = time;
  if (!isHlsStream.value && audioPlayer.value) {
    audioPlayer.value.currentTime = time;
  }
  playerState.media.currentTime = time;
};

// UI交互
const handleMouseEnter = () => {
  playerState.ui.controlsVisible = true;
  if (hideControlsTimer) {
    clearTimeout(hideControlsTimer);
    hideControlsTimer = null;
  }
};

const handleMouseLeave = () => {
  hideControlsTimer = setTimeout(() => {
    if (!playerState.ui.hoveringProgress) {
      playerState.ui.controlsVisible = false;
    }
  }, 2000);
};

// 错误处理
const handleHlsError = (data) => {
  if (data.fatal) {
    switch (data.type) {
      case Hls.ErrorTypes.NETWORK_ERROR:
        console.error('HLS network error, trying to recover');
        hls.value.startLoad();
        break;
      case Hls.ErrorTypes.MEDIA_ERROR:
        console.error('HLS media error, recovering');
        hls.value.recoverMediaError();
        break;
      default:
        initHls();
        break;
    }
  }
};

const initHls = () => {
  if (hls.value) {
    hls.value.destroy();
  }
  initializeHlsStream();
};

const handleVideoError = () => {
  if (isHlsStream.value && hls.value) {
    if (playerState.network.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
      playerState.media.loading = true;
      playerState.network.reconnectAttempts++;
      setTimeout(initHls, RECONNECT_INTERVAL);
    }
  } else {
    if (playerState.network.reconnectAttempts < MAX_RECONNECT_ATTEMPTS && !videoPlayer.value.paused) {
      playerState.media.loading = true;
      playerState.network.reconnectAttempts++;
      setTimeout(() => {
        videoPlayer.value.src = props.video.stream_video_url;
        videoPlayer.value.load();
        videoPlayer.value.play().catch(() => {
          handleVideoError();
        });
      }, RECONNECT_INTERVAL);
    }
  }
};

const handleAudioError = () => {
  if (!isHlsStream.value && 
      playerState.network.reconnectAttempts < MAX_RECONNECT_ATTEMPTS && 
      audioPlayer.value && 
      !audioPlayer.value.paused) {
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

// 触摸事件
const handleProgressTouchStart = (e) => {
  playerState.ui.isDragging = true;
  // 转换Touch事件为鼠标事件格式
  const touchEvent = { 
    clientX: e.touches[0].clientX,
    preventDefault: () => e.preventDefault(),
    currentTarget: e.currentTarget
  };
  handleProgressMouseDown(touchEvent);
};

const handleProgressTouchMove = (e) => {
  e.preventDefault();
  // 转换Touch事件为鼠标事件格式
  const touchEvent = { 
    clientX: e.touches[0].clientX,
    currentTarget: e.currentTarget
  };
  handleProgressHover(touchEvent);
};

const handleProgressTouchEnd = () => {
  playerState.ui.isDragging = false;
};

const handleTouchStart = () => {
  touchStartTime.value = Date.now();
};

const handleTouchEnd = () => {
  if (Date.now() - touchStartTime.value < 200) { // 短按
    if (Date.now() - lastTap.value < 300) { // 双击
      togglePlay();
    }
    lastTap.value = Date.now();
  }
};

// 屏幕方向
const handleOrientationChange = () => {
  if (screen.orientation.type.includes('landscape')) {
    videoPlayer.value.classList.add('landscape-mode');
  } else {
    videoPlayer.value.classList.remove('landscape-mode');
  }
};

// 资源清理
onUnmounted(() => {
  if (hideControlsTimer) {
    clearTimeout(hideControlsTimer);
    hideControlsTimer = null;
  }
  
  if (hls.value) {
    hls.value.destroy();
    hls.value = null;
  }
  
  screen.orientation?.removeEventListener('change', handleOrientationChange);
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
  @apply absolute bottom-0 left-0 right-0 h-[10px] cursor-pointer z-30;
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
  @apply text-white text-[1.2rem];
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

@media (hover: none) {
  .volume-slider-container {
    @apply w-20 !important;
  }
  .hover-gradient {
    @apply opacity-100 !important;
  }
}

@media (orientation: portrait) {
  .video-player {
    object-fit: contain;
  }
}

</style>
