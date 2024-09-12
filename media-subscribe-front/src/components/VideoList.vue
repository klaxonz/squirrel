<template>
  <TransitionGroup 
    name="video-list" 
    tag="div" 
    class="video-grid sm:grid sm:grid-cols-2 sm:gap-4 p-2"
  >
    <template v-if="loading && videos.length === 0">
      <div v-for="n in 10" :key="n" class="video-item-placeholder animate-pulse bg-gray-200 h-48"></div>
    </template>
    <template v-else>
      <VideoItem
        v-for="video in videos"
        :key="video.id"
        :video="video"
        @play="$emit('play', video)"
        @setVideoRef="$emit('setVideoRef', video.id, $event)"
        @videoPlay="$emit('videoPlay', video)"
        @videoPause="$emit('videoPause', video)"
        @videoEnded="$emit('videoEnded', video)"
        @fullscreenChange="$emit('fullscreenChange', $event)"
        @videoMetadataLoaded="$emit('videoMetadataLoaded', $event, video)"
        @toggleOptions="$emit('toggleOptions', video.id, $event)"
        @goToChannel="$emit('goToChannel', video.channel_id)"
      />
    </template>
  </TransitionGroup>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';
import VideoItem from './VideoItem.vue';

defineProps({
  videos: Array,
  loading: Boolean,
});

defineEmits([
  'play',
  'setVideoRef',
  'videoPlay',
  'videoPause',
  'videoEnded',
  'fullscreenChange',
  'videoMetadataLoaded',
  'toggleOptions',
  'goToChannel',
]);
</script>

<style scoped>
.video-grid {
  @apply grid-cols-1 sm:grid-cols-2;
  min-height: 100%;
  will-change: transform;
}

.video-list-move {
  transition: transform 0.5s ease;
}
</style>