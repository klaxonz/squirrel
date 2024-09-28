<template>
  <div class="grid grid-cols-6 gap-4">
    <VideoItem
      v-for="video in videos"
      :key="video.id"
      :video="video"
      :showAvatar="showAvatar"
      @play="$emit('play', video)"
      :setVideoRef="setVideoRef"
      @videoPlay="$emit('videoPlay', video)"
      @videoPause="$emit('videoPause', video)"
      @videoEnded="$emit('videoEnded', video)"
      @toggleOptions="$emit('toggleOptions', $event, video.id)"
      @goToChannel="$emit('goToChannel', video.channel_id)"
      @videoEnterViewport="$emit('videoEnterViewport', video)"
      @videoLeaveViewport="$emit('videoLeaveViewport', video)"
      @openModal="$emit('openModal', video)"
    />
  </div>
</template>

<script setup>
import VideoItem from './VideoItem.vue';

const props = defineProps({
  videos: Array,
  loading: Boolean,
  showAvatar: {
    type: Boolean,
    default: true
  },
  setVideoRef: Function,
});

const emit = defineEmits([
  'play',
  'videoPlay',
  'videoPause',
  'videoEnded',
  'toggleOptions',
  'goToChannel',
  'videoEnterViewport',
  'videoLeaveViewport',
  'openModal',
]);
</script>

<style scoped>
/* 保持现有样式不变 */
</style>