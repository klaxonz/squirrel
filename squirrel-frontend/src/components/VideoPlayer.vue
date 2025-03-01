<template>
  <div class="video-wrapper bg-[#0f0f0f]">
    <div class="video-container" 
      :class="{'pointer-events-none': isTouchDevice}"
      v-on="!isTouchDevice ? {
        mouseenter: handleMouseEnter,
        mouseleave: handleMouseLeave
      } : {}"
      @dblclick="!isTouchDevice && togglePlay()"
      @touchstart="handleTouchStart"
      @touchmove="handleTouchMove"
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

      <div class="video-click-layer" @click="handleVideoLayerClick">
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
      
      <div class="hover-gradient" v-if="playerState.ui.controlsVisible"></div>
      
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

      <!-- 添加快进/快退指示器 -->
      <div class="seeking-indicator" 
        v-if="playerState.ui.seeking.active"
        :data-direction="playerState.ui.seeking.direction"
      >
        <div class="seeking-content">
          <div class="seeking-icon-container">
            <Icon :icon="playerState.ui.seeking.direction === 'forward' ? 'material-symbols:fast-forward-rounded' : 'material-symbols:fast-rewind-rounded'" 
              class="seeking-icon" />
            <div class="seeking-seconds">
              {{ Math.round(Math.abs(playerState.ui.seeking.seekTime - playerState.media.currentTime)) }}秒
            </div>
          </div>
        </div>
      </div>

      <!-- 添加音量调节指示器 -->
      <div v-if="playerState.ui.volume.showIndicator" class="volume-adjust-indicator">
        <div class="volume-control-container">
          <div class="volume-slider">
            <div class="volume-slider-fill" :style="{ height: playerState.media.volume + '%' }"></div>
            <div class="volume-slider-thumb"></div>
          </div>
          <div class="volume-value">{{ Math.round(playerState.media.volume) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import {onMounted, watch, ref, computed, onUnmounted, reactive} from 'vue';
import { Icon } from '@iconify/vue';
import useVideoOperations from "../composables/useVideoOperations";
import { formatTime } from "../utils/dateFormat";
import Hls from 'hls.js';

const props = defineProps({
  video: Object
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
    bufferedProgress: 0,
    firstInteraction: true
  },
  // UI状态
  ui: {
    controlsVisible: true,
    fullscreen: false,
    hoveringProgress: false,
    hoverPosition: 0,
    previewTime: 0,
    showPlayIndicator: false,
    isDragging: false,
    previewSeekTime: 0,
    errorMessage: null,
    seeking: {
      active: false,
      startX: 0,
      currentX: 0,
      distance: 0,
      direction: null,
      seekTime: 0,
      wasPlaying: false
    },
    volume: {
      adjusting: false,
      startY: 0,
      startVolume: 0,
      showIndicator: false
    }
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

const hasAudioStream = computed(() => {
  return !!props.video?.stream_audio_url;
});

const isCanplay = computed(() => {
  if (!hasAudioStream.value) {
    return playerState.media.canPlay.video;
  }
  return playerState.media.canPlay.video && 
    (isHlsStream.value || playerState.media.canPlay.audio);
});

const isSeeking = computed(() => {
  if (!hasAudioStream.value) {
    return playerState.media.seeking.video;
  }
  return playerState.media.seeking.video || playerState.media.seeking.audio;
});

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

// 添加计算属性
const isTouchDevice = computed(() => 
  'ontouchstart' in window || navigator.maxTouchPoints > 0
);

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
  
  const syncInterval = setInterval(syncMedia, 2000);
  const showControlsInterval = setInterval(() => {
    if (playerState.media.playing) {
      playerState.ui.controlsVisible = false;
      clearInterval(showControlsInterval);
    }
  }, 3000);

  onUnmounted(() => {
    clearInterval(syncInterval);
  });
});

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
    
    // 如果有上次播放位置且是首次加载，则从该位置继续播放
    console.debug('video canplay, video last position', props.video, 'playerState.network.firstInteraction', playerState.network.firstInteraction);
    if (props.video?.last_position > 0 && playerState.media.firstInteraction) {
      console.debug('video canplay, set video time to', props.video.last_position);
      setVideoTime(props.video.last_position);
      playerState.media.firstInteraction = false;
    }
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
  if (!videoPlayer.value) return;

  if (playerState.media.playing) {
    // 暂停播放
    videoPlayer.value.pause();
    if (hasAudioStream.value && audioPlayer.value) {
      audioPlayer.value.pause();
    }
    playerState.media.playing = false;
    emit('pause');
  } else {
    // 开始播放
    if (playerState.network.firstInteraction) {
      playerState.network.firstInteraction = false;
    }
    
    videoPlayer.value.play().then(() => {
      playerState.media.playing = true;
      if (hasAudioStream.value && audioPlayer.value) {
        audioPlayer.value.play().catch(err => {
          console.error('Failed to play audio:', err);
        });
      }
      emit('play');
    }).catch(err => {

    });
  }
  
  playerState.ui.showPlayIndicator = true;
};

const toggleMute = () => {
  videoPlayer.value.muted = !videoPlayer.value.muted;
  if (!isHlsStream.value && audioPlayer.value) {
    audioPlayer.value.muted = videoPlayer.value.muted;
  }
  playerState.media.muted = videoPlayer.value.muted;
};

const toggleFullscreen = async () => {
  const elem = videoPlayer.value.parentElement;
  if (document.fullscreenElement) {
    await document.exitFullscreen();
  } else {
    if (elem.requestFullscreen) {
      await elem.requestFullscreen();
    } else if (elem.webkitRequestFullscreen) { /* Safari */
      await elem.webkitRequestFullscreen();
    } else if (elem.mozRequestFullScreen) { /* Firefox */
      await elem.mozRequestFullScreen();
    }
  }
  playerState.ui.fullscreen = !!document.fullscreenElement;
};

// 进度条交互
const handleProgressMouseDown = (e) => {
  e.preventDefault();
  playerState.ui.isDragging = true;
  const rect = e.currentTarget.getBoundingClientRect();
  
  const updatePreview = (clientX) => {
    const position = (clientX - rect.left) / rect.width;
    playerState.ui.previewSeekTime = playerState.media.duration * Math.min(Math.max(position, 0), 1);
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
  if(isTouchDevice.value) return;
  playerState.ui.controlsVisible = true;
  if (hideControlsTimer) {
    clearTimeout(hideControlsTimer);
    hideControlsTimer = null;
  }
};

const handleMouseLeave = () => {
  if(isTouchDevice.value) return;
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

// 改进触摸事件处理
const handleProgressTouchStart = (e) => {
  e.preventDefault(); // 防止滚动
  playerState.ui.isDragging = true;
  const rect = e.currentTarget.getBoundingClientRect();
  const position = (e.touches[0].clientX - rect.left) / rect.width;
  
  // 保存初始位置和时间
  playerState.ui.previewSeekTime = playerState.media.duration * Math.min(Math.max(position, 0), 1);
  playerState.ui.hoverPosition = position * 100;
  playerState.ui.hoveringProgress = true;
};

const handleProgressTouchMove = (e) => {
  e.preventDefault(); // 防止滚动
  
  if (playerState.ui.isDragging) {
    const rect = e.currentTarget.getBoundingClientRect();
    const position = (e.touches[0].clientX - rect.left) / rect.width;
    const boundedPosition = Math.min(Math.max(position, 0), 1);
    
    // 更新预览时间和位置
    playerState.ui.previewSeekTime = playerState.media.duration * boundedPosition;
    playerState.ui.hoverPosition = boundedPosition * 100;
  }
};

const handleProgressTouchEnd = (e) => {
  // 设置视频时间
  if (playerState.ui.isDragging) {
    setVideoTime(playerState.ui.previewSeekTime);
  }
  
  // 重置拖动状态
  playerState.ui.isDragging = false;
  playerState.ui.hoveringProgress = false;
};

const handleTouchStart = (e) => {
  const touch = e.touches[0];
  touchStartTime.value = Date.now();
  
  // 记录初始触摸位置
  playerState.ui.seeking.startX = touch.clientX;
  playerState.ui.seeking.currentX = touch.clientX;
  playerState.ui.volume.startY = touch.clientY;
  playerState.ui.volume.startVolume = playerState.media.volume;
  
  // 重置状态
  playerState.ui.seeking.active = false;
  playerState.ui.volume.adjusting = false;
};

const handleTouchMove = (e) => {
  if (e.touches.length !== 1) return;
  
  const touch = e.touches[0];
  const deltaX = Math.abs(touch.clientX - playerState.ui.seeking.startX);
  const deltaY = Math.abs(touch.clientY - playerState.ui.volume.startY);
  
  // 如果还没有确定滑动类型，根据滑动方向判断
  if (!playerState.ui.seeking.active && !playerState.ui.volume.adjusting) {
    // 降低触发阈值，让操作更灵敏
    if (deltaX > 5 || deltaY > 5) {
      // 如果横向移动距离大于纵向，则为快进快退
      if (deltaX > deltaY) {
        playerState.ui.seeking.active = true;
        // 记录开始时的播放状态
        playerState.ui.seeking.wasPlaying = playerState.media.playing;
        // 暂停播放以避免干扰
        if (playerState.media.playing) {
          videoPlayer.value.pause();
        }
      } else {
        playerState.ui.volume.adjusting = true;
        playerState.ui.volume.showIndicator = true;
      }
    }
  }
  
  // 根据已确定的滑动类型执行相应操作
  if (playerState.ui.volume.adjusting) {
    e.preventDefault();
    const volumeChange = ((playerState.ui.volume.startY - touch.clientY) / 200) * 100;
    const newVolume = Math.min(Math.max(playerState.ui.volume.startVolume + volumeChange, 0), 100);
    playerState.media.volume = newVolume;
  } else if (playerState.ui.seeking.active) {
    e.preventDefault(); // 防止页面滚动
    const touchX = touch.clientX;
    playerState.ui.seeking.currentX = touchX;
    
    const diffX = touchX - playerState.ui.seeking.startX;
    const absDiffX = Math.abs(diffX);
    
    // 降低触发阈值，提高响应性
    if (absDiffX > 20) {
      playerState.ui.seeking.distance = diffX;
      playerState.ui.seeking.direction = diffX > 0 ? 'forward' : 'backward';
      
      // 改进的非线性加速算法
      // 1. 基础速度更低，更容易控制：每30px对应2秒
      // 2. 使用平滑的指数曲线而不是阶梯式变化
      // 3. 最大速度限制，避免失控
      const baseSpeed = 2; // 基础速度：2秒/30px
      const maxSpeed = 30; // 最大速度限制：30秒
      const acceleration = Math.pow(absDiffX / 30, 1.5); // 使用指数1.5使加速更平滑
      const seekSeconds = Math.min(baseSpeed * acceleration, maxSpeed);
      
      if (playerState.ui.seeking.direction === 'forward') {
        playerState.ui.seeking.seekTime = Math.min(
          playerState.media.currentTime + seekSeconds,
          playerState.media.duration
        );
      } else {
        playerState.ui.seeking.seekTime = Math.max(
          playerState.media.currentTime - seekSeconds,
          0
        );
      }
      
      // 实时预览：直接更新视频时间，但不播放
      videoPlayer.value.currentTime = playerState.ui.seeking.seekTime;
    }
  }
};

const handleTouchEnd = (e) => {
  if (playerState.ui.volume.adjusting) {
    playerState.ui.volume.adjusting = false;
    setTimeout(() => {
      playerState.ui.volume.showIndicator = false;
    }, 1000);
    return;
  }

  if (playerState.ui.seeking.active) {
    setVideoTime(playerState.ui.seeking.seekTime);
    playerState.ui.seeking.active = false;
    playerState.ui.seeking.distance = 0;
    playerState.ui.seeking.direction = null;
    
    // 如果之前是播放状态，恢复播放
    if (playerState.ui.seeking.wasPlaying) {
      videoPlayer.value.play();
    }
    return;
  }

  // 原有点击逻辑
  const isTap = Date.now() - touchStartTime.value < 200;
  
  if (isTap) {
    if (Date.now() - lastTap.value < 300) {
      togglePlay();
      lastTap.value = 0;
      playerState.ui.controlsVisible = true;
    } else {
      playerState.ui.controlsVisible = !playerState.ui.controlsVisible;
      
      if (playerState.ui.controlsVisible) {
        if (hideControlsTimer) {
          clearTimeout(hideControlsTimer);
        }
        hideControlsTimer = setTimeout(() => {
          playerState.ui.controlsVisible = false;
        }, 3000);
      }
      
      lastTap.value = Date.now();
    }
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

// 更新同步函数
const syncMedia = () => {
  if (!videoPlayer.value || !hasAudioStream.value || !audioPlayer.value) return;
  
  // 只有在有音频流的情况下才进行同步
  const videoCurrent = videoPlayer.value.currentTime;
  const audioCurrent = audioPlayer.value.currentTime;

  // 只在差异较大时同步
  if (Math.abs(videoCurrent - audioCurrent) > 0.3) {
    audioPlayer.value.currentTime = videoCurrent;
  }
};

// 添加处理函数，区分设备类型
const handleVideoLayerClick = (e) => {
  // 检测是否为触摸设备
  const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
  
  // 触摸设备由touchend事件处理，不在这里处理
  if (isTouchDevice) {
    return;
  }
  
  // PC端直接调用togglePlay
  togglePlay();
};

</script>

<style scoped>
/* 提取公共变量 */
:root {
  --primary-red: #FF0000;
  --control-icon-size: 1.2rem;
  --progress-bar-height: 0.1875rem;
  --hover-transition: opacity 0.2s ease-in-out;
}

/* 合并重复的定位样式 */
.video-container,
.yt-loading-spinner,
.play-state-indicator,
.error-message,
.seeking-indicator {
  @apply absolute;
}

/* 简化transform写法 */
.transform-center {
  @apply top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2;
}

.play-state-indicator,
.error-message,
.seeking-indicator {
  @apply transform-center;
}

/* 合并颜色相关样式 */
.bg-semi-dark {
  background-color: rgba(0, 0, 0, 0.7);
}

/* 优化媒体查询 */
@media (hover: none), (pointer: coarse) {
  .volume-slider-container {
    width: 1.25rem !important;
  }
  .progress-bar {
    height: 0.3125rem;
  }
  .progress-bar-container {
    height: 1.25rem;
  }
}

/* 使用CSS变量优化重复值 */
.progress-bar-filled,
.progress-handle,
.progress-dot {
  background-color: var(--primary-red);
}

.control-icon {
  font-size: var(--control-icon-size);
}

/* 合并动画相关样式 */
@keyframes media-spinner {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.yt-spinner__circle {
  animation: media-spinner 1.4s linear infinite;
}

/* 优化伪类选择器 */
.volume-range {
  &::-webkit-slider-thumb,
  &::-moz-range-thumb {
    width: 0.75rem;
    height: 0.75rem;
    border-radius: 50%;
    background: white;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  }
}

/* 合并过渡效果 */
.video-controls,
.hover-gradient,
.progress-handle {
  transition: var(--hover-transition);
}

/* 使用:where()简化选择器 */
:where(.progress-container:hover, .video-controls:hover) .preview-time-tooltip {
  @apply opacity-100;
}

/* 优化flex布局声明 */
.controls-main,
.controls-left,
.controls-right,
.volume-slider-wrapper {
  @apply flex items-center;
}

/* 简化z-index管理 */
:root {
  --z-video-layer: 10;
  --z-controls: 20;
  --z-spinner: 30;
  --z-error: 40;
}

.video-click-layer { z-index: var(--z-video-layer); }
.video-controls { z-index: var(--z-controls); }
.yt-loading-spinner { z-index: var(--z-spinner); }
.error-message { z-index: var(--z-error); }

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
    opacity-100 transition-opacity duration-300;
}

.video-controls {
  @apply absolute bottom-0 left-0 right-0 px-4
    opacity-0 transition-all duration-200 z-20
    flex flex-col;
}

.controls-visible {
  @apply opacity-100;
  transition-delay: 0s;
}

.progress-container {
  @apply relative mb-0;
  height: 0.3125rem;
}

.preview-time-tooltip {
  @apply absolute bottom-8 bg-black/90 text-white rounded text-sm
    transform -translate-x-1/2 opacity-0 transition-opacity duration-200;
  padding: 0.25rem 0.5rem;
}

.progress-container:hover .preview-time-tooltip {
  @apply opacity-100;
}

.progress-bar-container {
  @apply absolute bottom-0 left-0 right-0 cursor-pointer z-30;
  height: 1rem;
  margin-bottom: -0.375rem;
}

.progress-bar {
  @apply relative w-full bg-[#FFFFFF33] overflow-hidden;
  height: 0.1875rem;
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
  @apply absolute bottom-1/2 rounded-full bg-[#FF0000]
    transform translate-y-1/2 -translate-x-1/2
    transition-opacity duration-200 opacity-0;
  width: 0.75rem;
  height: 0.75rem;
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
  height: 2.5rem;
}

.volume-slider-container {
  overflow: hidden;
  transition: width 0.2s;
  width: 0;
  height: 2.5rem;
  display: flex;
  align-items: center;
}

.volume-control:hover .volume-slider-container {
  width: 5rem;
}

.volume-slider-wrapper {
  position: relative;
  width: 100%;
  height: 2.5rem;
  display: flex;
  align-items: center;
  padding: 0 0.375rem;
}

.volume-track-bg {
  position: absolute;
  top: 50%;
  left: 0.375rem;
  right: 0.375rem;
  height: 0.1875rem;
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-50%);
  pointer-events: none;
  z-index: 1;
}

.volume-range-fill {
  position: absolute;
  height: 0.1875rem;
  background-color: white;
  left: 0.375rem;
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
  width: 0.375rem;
  height: 0.375rem;
  background-color: #FF0000;
  border-radius: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  transition: width 0.2s, height 0.2s;
}

.progress-bar-container:hover .progress-dot {
  width: 0.5rem;
  height: 0.5rem;
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
  bottom: 5.25rem;
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
  stroke-width: 0.375rem;
  stroke-linecap: round;
  color: white;
  animation: yt-spinner 1.4s linear infinite;
}

.yt-spinner__circle circle {
  stroke-dasharray: 12.5rem;
  stroke-dashoffset: 50rem;
}

.yt-spinner__circle {
  animation: media-spinner 1.4s linear infinite;
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
    @apply flex-nowrap justify-between w-full;
  }
  
  .controls-right {
    @apply mt-0 flex justify-end;
  }
  
  .controls-left {
    @apply flex justify-start;
  }
  
  /* 隐藏部分控件，简化移动端界面 */
  .controls-left .volume-control {
    @apply hidden;
  }
  
  /* 调整时间显示 */
  .time-display {
    @apply text-xs whitespace-nowrap;
  }
  
  /* 调整按钮大小 */
  .control-btn {
    @apply mx-1;
    padding: 0.25rem;
  }
  
  .control-icon {
    font-size: 1.2rem;
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
  height: 2.5rem;
  margin: 0;
  cursor: pointer;
  position: relative;
  z-index: 10;
}

/* 修复小圆点位置并与YouTube保持一致 */
.volume-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 50%;
  background: white;
  cursor: pointer;
  border: none;
  margin-top: -0.28125rem;
  z-index: 11;
  box-shadow: 0 0.0625rem 0.1875rem rgba(0, 0, 0, 0.2);
}

.volume-range::-moz-range-thumb {
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 50%;
  background: white;
  cursor: pointer;
  border: none;
  box-shadow: 0 0.0625rem 0.1875rem rgba(0, 0, 0, 0.2);
}

/* 设置轨道样式 */
.volume-range::-webkit-slider-runnable-track {
  width: 100%;
  height: 0.1875rem;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 0.09375rem;
}

/* 调整填充颜色 */
.volume-range-fill {
  background-color: white; /* 保持音量填充为白色 */
}

/* 确保其他样式保持不变 */
.volume-track-bg {
  background: rgba(255, 255, 255, 0.2); /* 保持浅灰色背景 */
}

/* 添加快进/快退指示器样式 */
.seeking-indicator {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
    z-30 flex items-center justify-center transition-all duration-300;
  background: rgba(28, 28, 28, 0.85);
  backdrop-filter: blur(0.75rem);
  -webkit-backdrop-filter: blur(0.75rem);
  border: 0.0625rem solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 0.5rem 2rem rgba(0, 0, 0, 0.2);
  width: 5rem;
  height: 5rem;
  border-radius: 1rem;
}

.seeking-content {
  @apply flex flex-col items-center justify-center relative;
  &::after {
    content: '';
    position: absolute;
    inset: -2.5rem;
    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 70%);
    opacity: 0.5;
    z-index: -1;
  }
}

.seeking-icon-container {
  @apply flex flex-col items-center;
  gap: 0.5rem;
}

.seeking-icon {
  @apply text-white transition-transform duration-300;
  font-size: 1.75rem;
  filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.2));
}

.seeking-seconds {
  @apply text-white/90 font-medium tracking-wide;
  font-size: 0.875rem;
  font-family: -apple-system, BlinkMacSystemFont, "YouTube Noto", Roboto, sans-serif;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

@keyframes seeking-pulse {
  0% {
    transform: translate(-50%, -50%) scale(0.98);
    opacity: 0.95;
  }
  50% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 1;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
  }
  100% {
    transform: translate(-50%, -50%) scale(0.98);
    opacity: 0.95;
  }
}

.seeking-indicator {
  animation: seeking-pulse 2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  
  &[data-direction="forward"] {
    .seeking-content::before {
      content: '';
      position: absolute;
      right: -1.25rem;
      width: 2.5rem;
      height: 100%;
      background: linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.1) 100%);
      transform: skewX(-15deg);
      opacity: 0;
      animation: slide-light 1.5s ease-in-out infinite;
    }
  }
  
  &[data-direction="backward"] {
    .seeking-content::before {
      content: '';
      position: absolute;
      left: -1.25rem;
      width: 2.5rem;
      height: 100%;
      background: linear-gradient(-90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.1) 100%);
      transform: skewX(15deg);
      opacity: 0;
      animation: slide-light 1.5s ease-in-out infinite;
    }
  }
}

@keyframes slide-light {
  0% {
    opacity: 0;
    transform: translateX(0) skewX(-15deg);
  }
  20% {
    opacity: 0.4;
  }
  80% {
    opacity: 0;
  }
  100% {
    opacity: 0;
    transform: translateX(100%) skewX(-15deg);
  }
}

.volume-adjust-indicator {
  @apply absolute left-1/2 -translate-x-1/2 top-[15%] flex flex-col items-center z-30;
  width: 8rem;
}

.volume-control-container {
  @apply relative flex flex-col items-center gap-1 w-full;
  padding: 0.5rem 0.75rem;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 0.5rem;
}

.volume-slider {
  @apply h-0.5 w-full bg-white/20 rounded-full relative overflow-hidden;
}

.volume-slider-fill {
  @apply absolute left-0 top-0 h-full bg-white/90 transition-all duration-100;
}

.volume-slider-thumb {
  @apply absolute w-2.5 h-2.5 bg-white rounded-full top-1/2 -translate-y-1/2 shadow-md;
  left: v-bind("playerState.media.volume + '%'");
  transition: left 0.1s ease-out;
}

.volume-value {
  @apply text-white/90 text-xs font-medium mt-1;
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
