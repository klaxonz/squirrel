<template>
  <div class="video-wrapper bg-[#0f0f0f]">
    <div class="video-container" 
      @mouseenter="handleMouseEnter"
      @mouseleave="handleMouseLeave"
      @dblclick="togglePlay"
      @touchstart="handleTouchStart"
      @touchend="handleTouchEnd"
      @keydown="handleKeyDown"
      tabindex="0"
      role="application"
      aria-label="视频播放器"
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
            @mousemove="debouncedProgressHover"
            @mouseleave="handleProgressLeave"
            @mousedown="handleProgressMouseDown"
            @touchstart="handleProgressTouchStart"
            @touchmove="handleProgressTouchMove"
            @touchend="handleProgressTouchEnd"
          >
            <div class="progress-bar">
              <div class="progress-bar-loaded" :style="{ width: playerState.media.bufferedProgress + '%' }"></div>
              <div class="progress-bar-filled" :style="{ width: progress + '%' }"></div>
            </div>
            <div class="progress-dot" :style="{ left: progress + '%' }" v-show="playerState.ui.hoveringProgress || playerState.ui.isDragging"></div>
            <div class="progress-handle" :style="{ left: progress + '%' }" v-show="playerState.ui.hoveringProgress"></div>
          </div>
        </div>
        
        <div class="controls-main">
          <div class="controls-left">
            <button @click="togglePlay" class="control-btn">
              <Icon v-if="playerState.media.playing" icon="material-symbols:pause" class="control-icon" />
              <Icon v-else icon="material-symbols:play-arrow" class="control-icon" />
            </button>
            
            <div class="time-display">
              {{ formatTime(playerState.media.currentTime) }} / {{ formatTime(playerState.media.duration) }}
            </div>
            
            <div class="volume-control group">
              <button @click="toggleMute" class="control-btn">
                <Icon :icon="volumeIcon" class="control-icon" />
              </button>
              
              <div class="volume-slider-container">
                <div class="volume-slider-wrapper">
                  <div class="volume-track-bg"></div>
                  <div 
                    class="volume-range-fill" 
                    :style="{ width: `${playerState.media.muted ? 0 : Math.min(playerState.media.volume, 100)}%` }"
                  ></div>
                  <input 
                    type="range" 
                    min="0" 
                    max="100" 
                    v-model="playerState.media.volume" 
                    class="volume-range"
                  >
                </div>
              </div>
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

      <!-- 添加错误消息提示 -->
      <div v-if="playerState.ui.errorMessage" class="error-message">
        <Icon icon="material-symbols:error" class="error-icon" />
        <span>{{ playerState.ui.errorMessage }}</span>
        <button @click="retryPlayback" class="retry-button">
          <Icon icon="material-symbols:refresh" />
          重试
        </button>
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

const emit = defineEmits(['play', 'pause', 'ended', 'fullscreenChange', 'timeupdate', 'error']);

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
    previewSeekTime: 0,
    errorMessage: null
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

// 改进防抖函数实现，确保事件对象正确传递
function debounce(fn, delay) {
  let timer = null;
  
  const debouncedFn = function(e) {
    // 保存原始事件对象，因为异步操作后可能无法访问
    if (e && e.type === 'mousemove') {
      // 对于鼠标事件，我们需要创建一个包含必要属性的对象
      const eventCopy = {
        clientX: e.clientX,
        clientY: e.clientY,
        currentTarget: e.currentTarget,
        target: e.target
      };
      
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        fn.call(this, eventCopy);
      }, delay);
    } else {
      // 其他类型的事件
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        fn.apply(this, arguments);
      }, delay);
    }
  };
  
  debouncedFn.cancel = function() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  };
  
  return debouncedFn;
}

// 修改进度条处理函数
const handleProgressHover = (e) => {
  try {
    // 检查事件对象
    if (!e || !e.currentTarget) {
      console.warn('Missing event properties in handleProgressHover');
      return;
    }
    
    playerState.ui.hoveringProgress = true;
    
    // 获取位置信息
    const rect = e.currentTarget.getBoundingClientRect();
    const position = ((e.clientX - rect.left) / rect.width) * 100;
    playerState.ui.hoverPosition = Math.min(Math.max(position, 0), 100);
    
    // 计算预览时间
    const duration = playerState.media.duration || 0;
    
    if (duration > 0) {
      if (playerState.ui.isDragging) {
        playerState.ui.previewTime = playerState.ui.previewSeekTime || 0;
      } else {
        playerState.ui.previewTime = (duration * position) / 100;
      }
    } else {
      const videoDuration = videoPlayer.value?.duration || 0;
      playerState.ui.previewTime = (videoDuration * position) / 100;
    }
  } catch (error) {
    console.error('Error in handleProgressHover:', error);
  }
};

// 在组件卸载时清理防抖函数
onUnmounted(() => {
  if (typeof debouncedProgressHover.cancel === 'function') {
    debouncedProgressHover.cancel();
  }
});

// 在声明函数后创建防抖版本
const debouncedProgressHover = debounce(handleProgressHover, 5);

const handleProgressLeave = () => {
  playerState.ui.hoveringProgress = false;
};

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
    
    // 确保duration被正确设置
    if (videoPlayer.value.duration && videoPlayer.value.duration !== Infinity) {
      playerState.media.duration = videoPlayer.value.duration;
    }
    
    emit('timeupdate', playerState.media.currentTime);
  }
};

const handleVideoProgress = () => {
  if (videoPlayer.value && videoPlayer.value.buffered.length > 0) {
    playerState.media.bufferedProgress = 
      (videoPlayer.value.buffered.end(0) / playerState.media.duration) * 100;
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
    // 使用requestAnimationFrame优化视觉更新
    requestAnimationFrame(() => {
      // 视觉更新代码
    });
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

// 改进HLS错误处理
const handleHlsError = (data) => {
  if (data.fatal) {
    switch (data.type) {
      case Hls.ErrorTypes.NETWORK_ERROR:
        console.warn('HLS network error, trying to recover');
        if (playerState.network.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          playerState.network.reconnectAttempts++;
          hls.value.startLoad();
        } else {
          playerState.ui.errorMessage = '网络连接失败，请检查您的网络后重试';
          emit('error', {type: 'network', message: 'Network connection failed'});
        }
        break;
      case Hls.ErrorTypes.MEDIA_ERROR:
        console.warn('HLS media error, recovering');
        hls.value.recoverMediaError();
        break;
      default:
        if (playerState.network.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          playerState.network.reconnectAttempts++;
          initHls();
        } else {
          emit('error', {type: 'fatal', message: 'Cannot play video'});
        }
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

// 添加键盘快捷键支持
const handleKeyDown = (e) => {
  // 防止在输入框中触发快捷键
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  
  switch(e.key) {
    case ' ':
    case 'k':
      togglePlay();
      e.preventDefault();
      break;
    case 'ArrowRight':
      setVideoTime(Math.min(playerState.media.currentTime + 5, playerState.media.duration));
      e.preventDefault();
      break;
    case 'ArrowLeft':
      setVideoTime(Math.max(playerState.media.currentTime - 5, 0));
      e.preventDefault();
      break;
    case 'm':
      toggleMute();
      e.preventDefault();
      break;
    case 'f':
      toggleFullscreen();
      e.preventDefault();
      break;
  }
};

// 添加播放重试方法
const retryPlayback = () => {
  playerState.ui.errorMessage = null;
  playerState.network.reconnectAttempts = 0;
  if (isHlsStream.value) {
    initHls();
  } else {
    videoPlayer.value.load();
    videoPlayer.value.play().catch(handleVideoError);
  }
};

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
  @apply absolute bottom-0 left-0 right-0 cursor-pointer z-30;
  height: 16px;
  margin-bottom: -6px;
}

.progress-bar {
  @apply relative w-full bg-[#FFFFFF33] overflow-hidden;
  height: 3px;
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
}

.progress-bar-loaded {
  @apply absolute top-0 left-0 h-full;
  background-color: rgba(255, 255, 255, 0.15);
}

.progress-bar-filled {
  @apply absolute top-0 left-0 h-full;
  background-color: #FF0000; /* 恢复为YouTube红色 */
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
  position: relative;
  display: flex;
  align-items: center;
  height: 40px;
}

.volume-slider-container {
  overflow: hidden;
  transition: width 0.2s;
  width: 0;
  height: 40px;
  display: flex;
  align-items: center;
}

.volume-control:hover .volume-slider-container {
  width: 80px;
}

.volume-slider-wrapper {
  position: relative;
  width: 100%;
  height: 40px;
  display: flex;
  align-items: center;
  padding: 0 6px;
}

.volume-track-bg {
  position: absolute;
  top: 50%;
  left: 6px;
  right: 6px;
  height: 3px;
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-50%);
  pointer-events: none;
  z-index: 1;
}

.volume-range-fill {
  position: absolute;
  height: 3px;
  background-color: white; /* 保持白色填充 */
  left: 6px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  z-index: 2;
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
  position: absolute;
  width: 6px;
  height: 6px;
  background-color: #FF0000;
  border-radius: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  transition: width 0.2s, height 0.2s;
}

.progress-bar-container:hover .progress-dot {
  width: 8px;
  height: 8px;
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

.error-message {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
    bg-black/80 text-white p-4 rounded flex flex-col items-center gap-2 z-50
    text-center max-w-[80%];
}

.error-icon {
  @apply text-red-500 text-3xl;
}

.retry-button {
  @apply mt-2 px-4 py-2 bg-red-600 rounded flex items-center gap-2
    hover:bg-red-700 transition-colors;
}

/* 响应式调整 */
@media (max-width: 640px) {
  .controls-main {
    @apply flex-wrap;
  }
  
  .controls-right {
    @apply mt-1;
  }
  
  .video-controls {
    @apply pb-2;
  }
  
  .time-display {
    @apply text-xs;
  }
}

/* 触摸优化 */
@media (hover: none) {
  .progress-bar {
    @apply h-[5px];
  }
  
  .progress-bar-container {
    @apply h-[20px];
  }
  
  .control-btn {
    @apply p-3;
  }
  
  .control-icon {
    @apply text-[1.4rem];
  }
}

/* 无障碍焦点样式 */
.video-container:focus-visible {
  @apply outline-white outline-offset-2 outline-2;
}

/* 将音量控制样式与YouTube保持一致 */
.volume-range {
  -webkit-appearance: none;
  appearance: none;
  background: transparent;
  width: 100%;
  height: 40px; /* 增大点击区域 */
  margin: 0;
  cursor: pointer;
  position: relative;
  z-index: 10;
}

/* 修复小圆点位置并与YouTube保持一致 */
.volume-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: white;
  cursor: pointer;
  border: none;
  margin-top: -4.5px; /* 关键：修复垂直位置 */
  z-index: 11;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.volume-range::-moz-range-thumb {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: white;
  cursor: pointer;
  border: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

/* 设置轨道样式 */
.volume-range::-webkit-slider-runnable-track {
  width: 100%;
  height: 3px;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.2); /* YouTube的浅灰色 */
  border-radius: 1.5px;
}

/* 调整填充颜色 */
.volume-range-fill {
  background-color: white; /* 保持音量填充为白色 */
}

/* 确保其他样式保持不变 */
.volume-track-bg {
  background: rgba(255, 255, 255, 0.2); /* 保持浅灰色背景 */
}
</style>
