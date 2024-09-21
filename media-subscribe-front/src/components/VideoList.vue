<template>
  <TransitionGroup 
    name="video-list" 
    tag="div" 
    class="video-grid sm:grid sm:grid-cols-2 sm:gap-4"
  >
    <template v-if="loading && videos.length === 0">
      <div v-for="n in 10" :key="`skeleton-${n}`" class="video-item-skeleton bg-white rounded-lg shadow-md p-3 mb-4">
        <div class="animate-pulse">
          <div class="bg-gray-300 h-40 w-full rounded-md mb-3"></div>
          <div class="flex items-center space-x-2 mb-2">
            <div class="rounded-full bg-gray-300 h-8 w-8"></div>
            <div class="h-4 bg-gray-300 rounded w-1/2"></div>
          </div>
          <div class="space-y-2">
            <div class="h-4 bg-gray-300 rounded w-3/4"></div>
            <div class="h-4 bg-gray-300 rounded w-1/2"></div>
          </div>
          <div class="mt-2 flex justify-between items-center">
            <div class="h-3 bg-gray-300 rounded w-1/4"></div>
            <div class="h-3 bg-gray-300 rounded w-1/4"></div>
          </div>
        </div>
      </div>
    </template>
    <template v-else-if="!loading && videos.length === 0">
      <div class="col-span-full text-center py-8">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mx-auto text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
        </svg>
        <p class="text-xl font-semibold text-gray-600">暂无视频</p>
        <p class="text-gray-500 mt-2">该标签页下还没有任何视频内容</p>
      </div>
    </template>
    <template v-else>
      <VideoItem
        v-for="video in videos"
        :key="video.id"
        :video="video"
        :showAvatar="showAvatar"
        :playbackError="playbackError"
        @play="$emit('play', video)"
        :setVideoRef="setVideoRef"
        @videoPlay="$emit('videoPlay', video)"
        @videoPause="$emit('videoPause', video)"
        @videoEnded="$emit('videoEnded', video)"
        @toggleOptions="$emit('toggleOptions', $event, video.id)"
        @goToChannel="$emit('goToChannel', video.channel_id)"
        @videoEnterViewport="$emit('videoEnterViewport', video)"
        @videoLeaveViewport="$emit('videoLeaveViewport', video)"
      />
    </template>
  </TransitionGroup>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';
import VideoItem from './VideoItem.vue';

const props = defineProps({
  videos: Array,
  loading: Boolean,
  showAvatar: {
    type: Boolean,
    default: true
  },
  playbackError: String,
  setVideoRef: Function,
});

defineEmits([
  'play',
  'videoPlay',
  'videoPause',
  'videoEnded',
  'toggleOptions',
  'goToChannel',
  'videoEnterViewport',
  'videoLeaveViewport',
]);
</script>

<style scoped>
.video-grid {
  @apply grid-cols-1 sm:grid-cols-2;
  min-height: 100%;
  will-change: transform;
}

.video-item-skeleton {
  @apply rounded-lg mb-4;
}
</style>