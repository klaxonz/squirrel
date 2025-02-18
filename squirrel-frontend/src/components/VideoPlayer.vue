<template>
  <div class="video-wrapper bg-[#0f0f0f]">
    <div class="video-container" 
      @mouseenter="handleMouseEnter"
      @mouseleave="handleMouseLeave"
    >
      <!-- 添加一个专门用于点击的遮罩层，不包括控件区域 -->
      <div class="video-click-layer" @click="togglePlay">
        <div class="play-state-indicator" v-if="showPlayIndicator">
          <Icon :icon="isPlaying ? 'material-symbols:pause' : 'material-symbols:play-arrow'" 
            class="indicator-icon" />
        </div>
      </div>

      <!-- 视频元素和其他内容 -->
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
      ></video>
      <audio
        ref="audioPlayer"
        :src="video.audio_stream_url"
        @seeking="handleAudioSeeking"
        @canplay="handleAudioCanplay"
      />
      
      <!-- Hover Gradient -->
      <div class="hover-gradient"></div>
      
      <!-- Custom Video Controls -->
      <div class="video-controls" :class="{ 'controls-visible': isControlsVisible }">
        <!-- Progress Bar Container -->
        <div class="progress-container">
          <!-- 预览时间气泡 -->
          <div class="preview-time-tooltip" :style="{ left: hoverPosition + '%' }" v-show="isHoveringProgress">
            {{ formatTime(previewTime) }}
          </div>
          
          <!-- 进度条 -->
          <div class="progress-bar-container"
            @mousemove="handleProgressHover"
            @mouseleave="handleProgressLeave"
            @mousedown="handleProgressClick"
          >
            <div class="progress-bar">
              <!-- 缓冲进度 -->
              <div class="progress-bar-loaded" :style="{ width: bufferedProgress + '%' }"></div>
              <!-- 播放进度 -->
              <div class="progress-bar-filled" :style="{ width: progress + '%' }">
                <!-- 添加进度小圆点 -->
                <div class="progress-dot"></div>
              </div>
              <!-- 预览进度 -->
              <div class="progress-bar-hover" :style="{ width: hoverPosition + '%' }" v-show="isHoveringProgress"></div>
            </div>
            <!-- 进度把手 -->
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
            
            <!-- 添加回时间显示 -->
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

// Add new ref for buffered progress
const bufferedProgress = ref(0);

// Computed properties for dynamic icons
const volumeIcon = computed(() => {
  if (isMuted.value || volume.value === 0) return 'material-symbols:volume-off';
  if (volume.value < 50) return 'material-symbols:volume-down';
  return 'material-symbols:volume-up';
});

const fullscreenIcon = computed(() => 
  isFullscreen.value ? 'material-symbols:fullscreen-exit' : 'material-symbols:fullscreen'
);

const progress = computed(() => 
  (currentTime.value / duration.value) * 100 || 0
);

const isHoveringProgress = ref(false);
const hoverPosition = ref(0);
const previewTime = ref(0);

// 添加控件显示状态
const isControlsVisible = ref(false);
let hideControlsTimer = null;

// 添加播放指示器状态
const showPlayIndicator = ref(false);

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

const isCanplay = () => {
  return isVideoCanplay && isAudioCanplay;
};

const isSeeking = () => {
  return isAudioSeeking || isVideoSeeking;
};

const handleVideoPlay = () => {
  firstCome = false;
  console.log('video play', isVideoCanplay, isAudioCanplay);
  if (isCanplay()) {
    audioPlayer.value.currentTime = videoPlayer.value.currentTime;
    audioPlayer.value.play();
    console.log(videoPlayer.value.currentTime, audioPlayer.value.currentTime);
  } else {
    videoPlayer.value.pause();
    audioPlayer.value.currentTime = videoPlayer.value.currentTime;
  }
  isPlaying.value = true;
};

const handleVideoPause = () => {
  console.log('video pause');
  if (audioPlayer.value) {
    audioPlayer.value.pause();
  }
  isPlaying.value = false;
};

const handleVideoSeeking = () => {
  console.log('video seeking');
  audioPlayer.value.pause();
  videoPlayer.value.pause();
  isAudioCanplay = false;
  isVideoCanplay = false;
  isVideoSeeking = true;
};

const handleVideoCanplay = () => {
  console.log('video canplay');
  isVideoCanplay = true;
  isVideoSeeking = false;
  if (!firstCome && !isSeeking() && isCanplay()) {
    videoPlayer.value.play();
    audioPlayer.value.play();
  }
};

const handleVideoWaiting = () => {
  console.log('video waiting');
  if (audioPlayer.value) {
    audioPlayer.value.pause();
  }
};

const handleAudioSeeking = () => {
  console.log('audio seeking');
  isAudioSeeking = true;
};

const handleAudioCanplay = () => {
  console.log('audio canplay');
  isAudioCanplay = true;
  isAudioSeeking = false;
  console.log('audio canplay', isSeeking(), isCanplay());
  if (!firstCome && !isSeeking() && isCanplay()) {
    videoPlayer.value.play();
    audioPlayer.value.play();
  }
};

// Control functions
const togglePlay = () => {
  if (videoPlayer.value.paused) {
    videoPlayer.value.play();
  } else {
    videoPlayer.value.pause();
  }
  isPlaying.value = !videoPlayer.value.paused;
  
  // 显示播放状态指示器
  showPlayIndicator.value = true;
  setTimeout(() => {
    showPlayIndicator.value = false;
  }, 500); // 500ms 后隐藏指示器
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

// Add time update handler
watch(videoPlayer, (player) => {
  if (player) {
    player.addEventListener('timeupdate', () => {
      currentTime.value = player.currentTime;
      duration.value = player.duration;
    });
  }
});

// Add volume change handler
watch(volume, (newVolume) => {
  if (videoPlayer.value) {
    videoPlayer.value.volume = newVolume / 100;
    audioPlayer.value.volume = newVolume / 100;
  }
});

// Add buffer progress tracking
watch(videoPlayer, (player) => {
  if (player) {
    player.addEventListener('progress', () => {
      if (player.buffered.length > 0) {
        bufferedProgress.value = (player.buffered.end(0) / player.duration) * 100;
      }
    });
  }
});

// 处理进度条悬停
const handleProgressHover = (e) => {
  isHoveringProgress.value = true;
  const rect = e.currentTarget.getBoundingClientRect();
  const position = ((e.clientX - rect.left) / rect.width) * 100;
  hoverPosition.value = Math.min(Math.max(position, 0), 100);
  previewTime.value = (duration.value * position) / 100;
};

const handleProgressLeave = () => {
  isHoveringProgress.value = false;
};

// 处理进度条点击和拖动
const handleProgressClick = (e) => {
  const rect = e.currentTarget.getBoundingClientRect();
  const position = (e.clientX - rect.left) / rect.width;
  const newTime = duration.value * position;
  
  videoPlayer.value.currentTime = newTime;
  audioPlayer.value.currentTime = newTime;
  
  // 添加拖动功能
  const handleMouseMove = (e) => {
    const position = (e.clientX - rect.left) / rect.width;
    const newTime = duration.value * Math.min(Math.max(position, 0), 1);
    videoPlayer.value.currentTime = newTime;
    audioPlayer.value.currentTime = newTime;
  };
  
  const handleMouseUp = () => {
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  };
  
  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
};

// 修改为 mouseenter 处理函数
const handleMouseEnter = () => {
  isControlsVisible.value = true;
  
  // 清除之前的定时器
  if (hideControlsTimer) {
    clearTimeout(hideControlsTimer);
  }
};

// 处理鼠标离开
const handleMouseLeave = () => {
  // 设置 2 秒后隐藏控件
  hideControlsTimer = setTimeout(() => {
    if (!isHoveringProgress.value) { // 如果不在拖动进度条，才隐藏
      isControlsVisible.value = false;
    }
  }, 2000);
};

// 在组件卸载时清理定时器
onUnmounted(() => {
  if (hideControlsTimer) {
    clearTimeout(hideControlsTimer);
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
  @apply absolute bottom-0 left-0 right-0 h-[5px] cursor-pointer;
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

.progress-bar-hover {
  @apply absolute top-0 left-0 h-full bg-[#FF0000] opacity-40;
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

/* Add YouTube-style font */
.video-controls {
  font-family: "YouTube Noto", Roboto, Arial, sans-serif;
}

/* 确保进度条交互时保持显示 */
.progress-container:hover ~ .video-controls,
.video-controls:hover {
  @apply opacity-100;
  transition-delay: 0s;
}

/* 添加进度小圆点样式 */
.progress-dot {
  @apply w-[6px] h-[6px] rounded-full bg-[#FF0000] absolute right-0
    transform translate-x-1/2 opacity-0 transition-opacity duration-200;
}

/* 悬停时显示小圆点 */
.progress-container:hover .progress-dot {
  @apply opacity-100;
}

/* 调整进度条悬停时的小圆点大小 */
.progress-bar:hover .progress-dot {
  @apply w-[8px] h-[8px];
}

/* 添加播放状态指示器样式 */
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
</style>
