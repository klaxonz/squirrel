<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-90">
    <div class="relative w-full h-full max-w-7xl max-h-[90vh] mx-auto bg-black rounded-lg shadow-lg overflow-hidden">
      <div class="absolute top-4 right-4 z-10">
        <button @click="close" class="text-white hover:text-gray-300 transition-colors">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
      <div class="w-full h-full flex flex-col">
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
        <div class="p-4 bg-white">
          <h2 class="text-lg font-semibold text-gray-900">{{ video?.title }}</h2>
          <p class="mt-1 text-sm text-gray-600">{{ video?.channel_name }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';
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
</script>