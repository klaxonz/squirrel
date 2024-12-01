<template>
  <div v-if="currentEpisode?.audio_url" class="podcast-player fixed bottom-0 left-0 right-0 bg-[#1f1f1f] border-t border-[#272727]">
    <!-- 进度条区域 -->
    <div class="relative group">
      <!-- 进度条 -->
      <div 
        class="flex items-center" 
      >
        <!-- 当前时间 -->
        <span class="text-xs text-[#aaaaaa] w-16 text-center">{{ formatTime(audio.currentTime) }}</span>
        
        <!-- 进度条 -->
        <div 
          class="flex-1 h-[2px] bg-[#3f3f3f] cursor-pointer relative hover:h-1 transition-all"
          @click="handleProgressClick"
          @mousemove="handleProgressHover"
          @mouseleave="showHoverTime = false"
        >
          <div 
            class="h-full bg-[#cc0000] relative transition-all duration-200"
            :style="{ width: `${progress * 100}%` }"
          >
            <div class="absolute right-0 top-1/2 -translate-y-1/2 w-2 h-2 bg-white rounded-full transform translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity"></div>
          </div>
          <!-- 悬停时间提示 -->
          <div 
            v-if="showHoverTime" 
            class="absolute top-0 -translate-y-full text-xs text-white bg-black/80 px-2 py-1 rounded transform -translate-x-1/2 pointer-events-none"
            :style="{ left: `${hoverPosition}%` }"
          >
            {{ formatTime(hoverTime) }}
          </div>
        </div>
        
        <!-- 总时长 -->
        <span class="text-xs text-[#aaaaaa] w-16 text-center">{{ formatTime(audio.duration) }}</span>
      </div>
    </div>

    <!-- 控制栏 -->
    <div class="flex items-center h-14 px-4">
      <!-- 封面和信息 -->
      <img 
        :src="podcast.cover_url" 
        :alt="podcast.title"
        class="w-9 h-9 rounded object-cover"
      >
      <div class="ml-3 flex-grow min-w-0">
        <h4 class="text-sm font-medium line-clamp-1">{{ currentEpisode.title }}</h4>
        <p class="text-xs text-[#aaaaaa] line-clamp-1">{{ podcast.title }}</p>
      </div>

      <!-- 控制按钮 -->
      <div class="flex items-center space-x-4">
        <!-- 后退15秒 -->
        <button class="p-1.5 hover:bg-[#272727] rounded-full" @click="seekBackward">
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12.5 3C17.15 3 21 6.85 21 11.5c0 4.65-3.85 8.5-8.5 8.5-4.65 0-8.5-3.85-8.5-8.5h2c0 3.54 2.96 6.5 6.5 6.5 3.54 0 6.5-2.96 6.5-6.5S15.04 5 11.5 5V8L6 4l5.5-4v3z"/>
          </svg>
        </button>

        <!-- 播放/暂停 -->
        <button class="p-2 hover:bg-[#272727] rounded-full" @click="togglePlay">
          <svg v-if="isPlaying" class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
            <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
          </svg>
          <svg v-else class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z"/>
          </svg>
        </button>

        <!-- 前进15秒 -->
        <button class="p-1.5 hover:bg-[#272727] rounded-full" @click="seekForward">
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M11.5 3c4.65 0 8.5 3.85 8.5 8.5 0 4.65-3.85 8.5-8.5 8.5-4.65 0-8.5-3.85-8.5-8.5h2c0 3.54 2.96 6.5 6.5 6.5 3.54 0 6.5-2.96 6.5-6.5S15.04 5 11.5 5V8L6 4l5.5-4v3z"/>
          </svg>
        </button>

        <!-- 音量控制 -->
        <div class="flex items-center space-x-2">
          <button class="p-1.5 hover:bg-[#272727] rounded-full" @click="toggleMute">
            <svg v-if="volume > 0" class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
            </svg>
            <svg v-else class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>
            </svg>
          </button>
          <input 
            type="range" 
            min="0" 
            max="100" 
            v-model="volume"
            class="w-16 accent-[#cc0000]"
          >
        </div>

        <!-- 播放速度 -->
        <button 
          class="px-2 py-1 text-xs hover:bg-[#272727] rounded"
          @click="toggleSpeedMenu"
        >
          {{ playbackRate }}x
        </button>
      </div>
    </div>

    <!-- 播放速度菜单 -->
    <div 
      v-if="showSpeedMenu"
      class="absolute bottom-full right-4 mb-2 bg-[#272727] rounded-lg overflow-hidden shadow-lg"
    >
      <div 
        v-for="speed in [0.5, 0.75, 1, 1.25, 1.5, 2]"
        :key="speed"
        class="px-4 py-2 hover:bg-[#3f3f3f] cursor-pointer"
        :class="{ 'bg-[#3f3f3f]': playbackRate === speed }"
        @click="setPlaybackRate(speed)"
      >
        {{ speed }}x
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue';
import { throttle } from 'lodash-es';  // 添加 throttle 工具

const props = defineProps({
  podcast: {
    type: Object,
    required: true
  },
  currentEpisode: {
    type: Object,
    required: true
  },
  isPlaying: Boolean
});

const emit = defineEmits(['play', 'pause', 'timeupdate']);

const audio = ref(new Audio());
const progress = ref(0);
const volume = ref(100);
const playbackRate = ref(1);
const showSpeedMenu = ref(false);
const showHoverTime = ref(false);
const hoverPosition = ref(0);
const hoverTime = ref(0);
const ws = ref(null);

// WebSocket连接管理
const setupWebSocket = (episodeId) => {
  console.log('Setting up WebSocket for episode:', episodeId); // 调试日志
  
  // 关闭旧连接
  if (ws.value) {
    ws.value.close();
  }

  // 建立新连接
  const wsUrl = `ws://localhost:8000/api/podcasts/episodes/${episodeId}/ws`;
  console.log('WebSocket URL:', wsUrl); // 调试日志
  
  ws.value = new WebSocket(wsUrl);
  
  ws.value.onopen = () => {
    console.log('WebSocket connected');
    // 连接建立后发送初始进度
    if (audio.value.duration) {
      ws.value.send(JSON.stringify({
        position: Math.floor(audio.value.currentTime),
        duration: Math.floor(audio.value.duration)
      }));
    }
  };
  
  ws.value.onerror = (error) => {
    console.error('WebSocket error:', error);
  };
  
  ws.value.onclose = () => {
    console.log('WebSocket closed');
  };
};

// 创建节流版本的更新函数
const throttledUpdateProgress = throttle((position, duration) => {
  if (ws.value && ws.value.readyState === WebSocket.OPEN) {
    ws.value.send(JSON.stringify({
      position: Math.floor(position),
      duration: Math.floor(duration)
    }));
  }
}, 5000);  // 每5秒最多发送一次

// 初始化音频
watch(() => props.currentEpisode?.audio_url, (newUrl) => {
  console.log('Audio URL changed:', newUrl);
  if (newUrl) {
    try {
      console.log('Setting audio source:', newUrl);
      audio.value.src = newUrl;
      audio.value.volume = volume.value / 100;
      audio.value.playbackRate = playbackRate.value;
      
      // 等待音频加载完成后再播放
      const handleCanPlay = () => {
        console.log('Audio can play now');
        if (props.isPlaying) {
          console.log('Attempting to play audio');
          const playPromise = audio.value.play();
          if (playPromise !== undefined) {
            playPromise.catch(error => {
              console.error('播放失败:', error);
              emit('pause');
            });
          }
        }
        // 移除事件监听
        audio.value.removeEventListener('canplay', handleCanPlay);
      };
      
      // 添加音频加载事件监听
      audio.value.addEventListener('canplay', handleCanPlay);
      
      audio.value.addEventListener('loadeddata', () => {
        console.log('Audio loaded successfully');
      });
      
      audio.value.addEventListener('error', (e) => {
        console.error('Audio loading error:', e);
        emit('pause');
      });
    } catch (error) {
      console.error('设置音频源失败:', error);
      emit('pause');
    }
  }
}, { immediate: true });

// 播放控制
watch(() => props.isPlaying, (isPlaying) => {
  console.log('Playing state changed:', isPlaying, audio.value.src);
  if (!isPlaying && audio.value.src) {
    audio.value.pause();
  }
}, { immediate: true });

// 音量控制
watch(volume, (newVolume) => {
  audio.value.volume = newVolume / 100;
});

// 播放速度
const setPlaybackRate = (rate) => {
  playbackRate.value = rate;
  audio.value.playbackRate = rate;
  showSpeedMenu.value = false;
};

// 格式化时间
const formatTime = (seconds) => {
  if (!seconds || isNaN(seconds)) return '00:00';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

// 进度更新
audio.value.addEventListener('timeupdate', () => {
  const currentTime = audio.value.currentTime;
  const duration = audio.value.duration;
  
  // 更新本地进度显示
  progress.value = currentTime / duration;
  
  // 发送进度到服务器
  throttledUpdateProgress(currentTime, duration);
});

// 在关键时刻强制更新
const criticalUpdatePoints = () => {
  if (ws.value && ws.value.readyState === WebSocket.OPEN && audio.value.src) {
    ws.value.send(JSON.stringify({
      position: Math.floor(audio.value.currentTime),
      duration: Math.floor(audio.value.duration)
    }));
  }
};

// 监听剧集变化
watch(() => props.currentEpisode?.id, (newId) => {
  console.log('Episode changed:', newId); // 调试日志
  if (newId) {
    setupWebSocket(newId);
  }
}, { immediate: true }); // 添加 immediate: true 以确保首次加载时也会执行

// 组件卸载时清理
onUnmounted(() => {
  if (ws.value) {
    ws.value.close();
  }
  throttledUpdateProgress.cancel();
});

// 控制函数
const togglePlay = () => {
  if (props.isPlaying) {
    emit('pause');
  } else {
    emit('play');
  }
};

const seekBackward = () => {
  audio.value.currentTime = Math.max(0, audio.value.currentTime - 15);
};

const seekForward = () => {
  audio.value.currentTime = Math.min(audio.value.duration, audio.value.currentTime + 15);
};

const toggleMute = () => {
  if (volume.value > 0) {
    volume.value = 0;
  } else {
    volume.value = 100;
  }
};

const handleProgressClick = (event) => {
  const rect = event.currentTarget.getBoundingClientRect();
  const percent = (event.clientX - rect.left) / rect.width;
  audio.value.currentTime = percent * audio.value.duration;
};

const toggleSpeedMenu = () => {
  showSpeedMenu.value = !showSpeedMenu.value;
};

// 组件挂载时初始化
onMounted(() => {
  if (props.currentEpisode?.audio_url) {
    console.log('Initializing audio on mount:', props.currentEpisode.audio_url);
    audio.value.src = props.currentEpisode.audio_url;
    audio.value.volume = volume.value / 100;
    audio.value.playbackRate = playbackRate.value;
  }
});

// 处理进度条悬停
const handleProgressHover = (event) => {
  const rect = event.currentTarget.getBoundingClientRect();
  const percent = (event.clientX - rect.left) / rect.width;
  hoverPosition.value = percent * 100;
  hoverTime.value = percent * audio.value.duration;
  showHoverTime.value = true;
};
</script> 