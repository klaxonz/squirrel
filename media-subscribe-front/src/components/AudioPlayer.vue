<template>
  <div 
    v-show="isVisible"
    v-if="episode"
    class="fixed bottom-6 left-1/2 -translate-x-1/2 bg-[#282828] rounded-lg shadow-lg overflow-hidden w-[420px] transition-opacity duration-200"
  >
    <div class="flex flex-col">
      <!-- 主界面 -->
      <div class="flex items-center p-1.5">
        <!-- 左侧信息区域 -->
        <div class="flex items-center gap-2 flex-grow min-w-0 mr-2">
          <img
            :src="episode.cover_url || channel?.cover_url"
            :alt="episode.title"
            class="w-7 h-7 rounded object-cover flex-shrink-0"
            referrerpolicy="no-referrer"
          />
          <div class="flex-grow min-w-0">
            <h3 class="text-white text-[11px] font-medium line-clamp-1 tracking-wide">{{ episode.title }}</h3>
            <div class="text-[9px] text-[#aaaaaa] mt-0.5">
              {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
            </div>
          </div>
        </div>
        
        <!-- 控制按钮 -->
        <div class="flex items-center gap-1">
          <button 
            @click="skipBackward"
            class="p-1 text-[#aaaaaa] hover:text-white rounded-full hover:bg-[#3f3f3f] transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
              <path d="M8.445 14.832A1 1 0 0010 14v-2.798l5.445 3.63A1 1 0 0017 14V6a1 1 0 00-1.555-.832L10 8.798V6a1 1 0 00-1.555-.832l-6 4a1 1 0 000 1.664l6 4z" />
            </svg>
          </button>
          <button 
            @click="togglePlay"
            class="p-1 text-white rounded-full bg-white hover:bg-gray-200 transition-colors"
          >
            <svg v-if="!isPlaying" xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 text-black" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 text-black" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
          </button>
          <button 
            @click="skipForward"
            class="p-1 text-[#aaaaaa] hover:text-white rounded-full hover:bg-[#3f3f3f] transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
              <path d="M4.555 5.168A1 1 0 003 6v8a1 1 0 001.555.832L10 11.202V14a1 1 0 001.555.832l6-4a1 1 0 000-1.664l-6-4A1 1 0 0010 6v2.798L4.555 5.168z" />
            </svg>
          </button>
          <button 
            @click="$emit('close')"
            class="p-1 text-[#aaaaaa] hover:text-white rounded-full hover:bg-[#3f3f3f] transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-2.5 w-2.5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- 进度条 -->
      <div class="px-2 pb-1">
        <div class="relative h-0.5 bg-[#4f4f4f] rounded-full cursor-pointer" @click="seek">
          <div 
            class="absolute left-0 top-0 h-full bg-white rounded-full transition-all"
            :style="{ width: `${progress}%` }"
          ></div>
          <div class="absolute left-0 right-0 top-0 bottom-0 opacity-0 hover:opacity-100 transition-opacity">
            <div class="absolute left-0 top-0 h-full bg-white/30 rounded-full"
                 :style="{ width: `${progress}%` }">
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 实际的音频元素 -->
    <audio
      ref="audioRef"
      :src="episode.audio_url"
      @timeupdate="onTimeUpdate"
      @loadedmetadata="onLoadedMetadata"
      @ended="onEnded"
      @play="isPlaying = true"
      @pause="isPlaying = false"
    ></audio>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';

const props = defineProps({
  episode: Object,
  channel: Object
});

const emit = defineEmits(['ended', 'close']);

const audioRef = ref(null);
const isPlaying = ref(false);
const currentTime = ref(0);
const duration = ref(0);
const progress = ref(0);

// 添加显隐控制
const isVisible = ref(true);

// 监听 episode 变化，自动播放新的剧集
watch(() => props.episode?.id, (newId, oldId) => {
  if (newId && newId !== oldId) {
    // 等待 DOM 更新后再播放
    nextTick(() => {
      if (audioRef.value) {
        audioRef.value.play().catch(error => {
          console.error('Auto-play failed:', error);
        });
      }
    });
  }
});

// 播放控制
const togglePlay = async () => {
  if (!audioRef.value) return;
  
  try {
    if (audioRef.value.paused) {
      await audioRef.value.play();
      isPlaying.value = true;
    } else {
      audioRef.value.pause();
      isPlaying.value = false;
    }
  } catch (error) {
    console.error('Play/pause failed:', error);
    isPlaying.value = false;
  }
};

// 快进快退
const skipForward = () => {
  audioRef.value.currentTime += 15;
};

const skipBackward = () => {
  audioRef.value.currentTime -= 15;
};

// 进度条点击跳转
const seek = (event) => {
  const rect = event.currentTarget.getBoundingClientRect();
  const percent = (event.clientX - rect.left) / rect.width;
  audioRef.value.currentTime = percent * duration.value;
};

// 事件处理
const onTimeUpdate = () => {
  if (!audioRef.value) return;
  currentTime.value = audioRef.value.currentTime;
  progress.value = (currentTime.value / duration.value) * 100;
  isPlaying.value = !audioRef.value.paused;  // 确保播放状态正确
};

const onLoadedMetadata = () => {
  if (!audioRef.value) return;
  duration.value = audioRef.value.duration;
  isPlaying.value = !audioRef.value.paused;  // 确保初始状态正确
};

const onEnded = () => {
  isPlaying.value = false;
  emit('ended');
};

// 格式化时间
const formatTime = (seconds) => {
  if (!seconds) return '00:00:00';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

// 修改键盘控制
const handleKeyPress = (event) => {
  if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
    return;
  }

  // 检查是否按下 Ctrl + Alt + P
  if (event.code === 'KeyP' && event.ctrlKey && event.altKey) {
    event.preventDefault();
    isVisible.value = !isVisible.value;
  } else if (event.code === 'Space' && !event.ctrlKey && !event.altKey) {
    event.preventDefault();
    togglePlay();
  }
};

onMounted(() => {
  document.addEventListener('keydown', handleKeyPress);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyPress);
});
</script>

<style scoped>
.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.shadow-lg {
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
}

h3 {
  transition: color 0.2s ease;
}

h3:hover {
  color: #ffffff;
}
</style> 