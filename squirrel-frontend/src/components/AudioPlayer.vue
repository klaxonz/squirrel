<template>
  <div
    v-show="isVisible"
    v-if="episode"
    class="fixed bottom-6 left-1/2 -translate-x-1/2 bg-bg-card rounded-lg shadow-lg overflow-hidden w-80 transition-opacity duration-200 sm:w-96"
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
            <h3 class="text-text-primary text-xs font-medium line-clamp-1 tracking-wide">{{ episode.title }}</h3>
            <div class="text-2xs text-text-muted mt-0.5">
              {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
            </div>
          </div>
        </div>

        <!-- 控制按钮 -->
        <div class="flex items-center gap-1">
          <button
            @click="skipBackward"
            class="p-1 text-text-muted hover:text-text-primary rounded-full hover:bg-bg-hover transition-colors"
          >
            <BackwardIcon class="h-3 w-3" />
          </button>
          <button
            @click="togglePlay"
            class="p-1 text-text-primary rounded-full bg-bg-elevated hover:bg-bg-hover transition-colors"
          >
            <PlayIcon v-if="!isPlaying" class="h-3 w-3" />
            <PauseIcon v-else class="h-3 w-3" />
          </button>
          <button
            @click="skipForward"
            class="p-1 text-text-muted hover:text-text-primary rounded-full hover:bg-bg-hover transition-colors"
          >
            <ForwardIcon class="h-3 w-3" />
          </button>
          <button
            @click="$emit('close')"
            class="p-1 text-text-muted hover:text-text-primary rounded-full hover:bg-bg-hover transition-colors"
          >
            <XMarkIcon class="h-2.5 w-2.5" />
          </button>
        </div>
      </div>

      <!-- 进度条 -->
      <div class="px-2 pb-1">
        <div class="relative h-0.5 bg-bg-tertiary rounded-full cursor-pointer" @click="seek">
          <div
            class="absolute left-0 top-0 h-full bg-bg-elevated rounded-full transition-all"
            :style="{ width: `${progress}%` }"
          ></div>
          <div class="absolute left-0 right-0 top-0 bottom-0 opacity-0 hover:opacity-100 transition-opacity">
            <div class="absolute left-0 top-0 h-full bg-bg-elevated/30 rounded-full"
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
import {
  BackwardIcon,
  PlayIcon,
  PauseIcon,
  ForwardIcon,
  XMarkIcon
} from '@heroicons/vue/24/outline';

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
  isPlaying.value = !audioRef.value.paused;
};

const onLoadedMetadata = () => {
  if (!audioRef.value) return;
  duration.value = audioRef.value.duration;
  isPlaying.value = !audioRef.value.paused;
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
  box-shadow: var(--shadow-lg);
}

h3 {
  transition: color 0.2s ease;
}

h3:hover {
  color: var(--text-accent);
}
</style>
