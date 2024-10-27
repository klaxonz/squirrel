<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black" @keydown.esc="close" tabindex="0">
    <div class="relative w-full h-full bg-[#0f0f0f]">
      <div class="absolute top-4 right-4 z-10">
        <button @click="close" class="text-[#aaaaaa] hover:text-white transition-colors">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
      <div class="flex flex-col h-full">
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
          <h2 class="text-lg font-semibold text-white">{{ video?.title }}</h2>
          <div class="mt-2 flex items-center">
            <img 
              :src="video?.channel_avatar" 
              alt="Channel Avatar" 
              class="w-10 h-10 rounded-full mr-3 object-cover"
              referrerpolicy="no-referrer"
            >
            <div>
              <p class="text-sm font-medium text-white">{{ video?.channel_name }}</p>
              <p class="text-xs text-[#aaaaaa]">{{ formatDate(video?.uploaded_at) }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, onMounted, onUnmounted } from 'vue';
import VideoPlayer from './VideoPlayer.vue';

const props = defineProps({
  isOpen: Boolean,
  video: Object,
  setVideoRef: Function,
});

const emit = defineEmits(['close', 'videoPlay', 'videoPause', 'videoEnded']);

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
/* 可以添加任何额外的样式 */
</style>
