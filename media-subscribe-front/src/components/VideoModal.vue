<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black" @keydown.esc="close" tabindex="0">
    <div class="relative w-full h-full bg-[#0f0f0f] flex">
      <!-- 视频播放区域 -->
      <div class="flex-grow flex flex-col h-full">
        <div class="flex-grow relative">
          <VideoPlayer
            v-if="video"
            :key="video.id"
            :video="video"
            :setVideoRef="setVideoRef"
            @play="onVideoPlay"
            @pause="onVideoPause"
            @ended="onVideoEnded"
            class="w-full h-full"
          />
        </div>
        <div class="p-4 bg-[#0f0f0f] border-t border-[#272727]">
          <div class="flex items-baseline">
            <h2 class="text-lg font-semibold text-white mr-2">{{ video?.title }}</h2>
            <span class="text-xs text-[#aaaaaa]">{{ formatDate(video?.uploaded_at) }}</span>
          </div>
          <div class="mt-2 flex items-center">
            <img 
              :src="video?.channel_avatar" 
              alt="Channel Avatar" 
              class="w-10 h-10 rounded-full mr-3 object-cover"
              referrerpolicy="no-referrer"
            >
            <p class="text-sm font-medium text-white">{{ video?.channel_name }}</p>
          </div>
        </div>
      </div>

      <!-- 播放列表 -->
      <div class="w-96 h-full bg-[#181818] flex flex-col">
        <div class="text-white text-lg font-semibold p-4 border-b border-[#272727] flex items-center relative">
          <span>播放列表</span>
          <span class="text-sm text-[#aaaaaa] ml-2">{{ currentIndex + 1 }} / {{ playlist.length }}</span>
          <button 
            @click="close" 
            class="absolute right-4 top-1/2 transform -translate-y-1/2 text-[#aaaaaa] hover:text-white transition-colors duration-150 focus:outline-none"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>
        <div class="flex-grow overflow-y-auto custom-scrollbar">
          <div v-for="(item, index) in playlist" :key="item.id" 
               class="flex items-start p-2 hover:bg-[#272727] cursor-pointer"
               :class="{ 'bg-[#383838]': item.id === video?.id }"
               @click="changeVideo(item)">
            <div class="w-40 h-[5.625rem] relative mr-3 flex-shrink-0">
              <img :src="item.thumbnail" alt="Video thumbnail" class="w-full h-full object-cover">
              <span class="absolute bottom-1 right-1 bg-black bg-opacity-70 text-white text-xs px-1 rounded">
                {{ formatDuration(item.duration) }}
              </span>
            </div>
            <div class="flex-grow min-w-0">
              <p class="text-white text-sm line-clamp-2" :class="{ 'font-semibold': item.id === video?.id }">{{ item.title }}</p>
              <p class="text-[#aaaaaa] text-xs mt-1 truncate">{{ item.channel_name }}</p>
            </div>
            <div v-if="item.id === video?.id" class="ml-2 text-[#aaaaaa] flex-shrink-0">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, onMounted, onUnmounted, ref, computed } from 'vue';
import VideoPlayer from './VideoPlayer.vue';

const props = defineProps({
  isOpen: Boolean,
  video: Object,
  setVideoRef: Function,
  playlist: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(['close', 'videoPlay', 'videoPause', 'videoEnded', 'changeVideo']);

const currentIndex = computed(() => {
  return props.playlist.findIndex(item => item.id === props.video?.id);
});

const close = () => {
  emit('close');
};

const onVideoPlay = () => {
  emit('videoPlay', props.video);
};

const onVideoPause = () => {
  emit('videoPause', props.video);
};

const onVideoEnded = () => {
  emit('videoEnded', props.video);
};

const changeVideo = (newVideo) => {
  emit('changeVideo', newVideo);
};

const formatDate = (dateString) => {
  if (!dateString) return '未知日期';
  const date = new Date(dateString);
  const now = new Date();
  const diffTime = Math.abs(now - date);
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  if (diffDays === 1) return '1 天前';
  if (diffDays <= 7) return `${diffDays} 天前`;
  if (diffDays <= 30) return `${Math.ceil(diffDays / 7)} 周前`;
  if (diffDays <= 365) return `${Math.ceil(diffDays / 30)} 个月前`;
  return `${Math.ceil(diffDays / 365)} 年前`;
};

const formatDuration = (seconds) => {
  if (!seconds) return '未知';
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

const handleKeyDown = (event) => {
  if (event.key === 'Escape') {
    close();
  }
};

onMounted(() => {
  document.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown);
});
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.custom-scrollbar {
  scrollbar-width: thin;
  scrollbar-color: #606060 #181818;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 2px; /* 将宽度从 4px 减小到 2px */
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: #181818;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #606060;
  border-radius: 1px; /* 将圆角从 2px 减小到 1px */
  border: none; /* 移除边框 */
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: #909090;
}

button:focus {
  outline: none;
}
</style>
