<template>
  <div class="grid grid-cols-5 gap-4">
    <VideoItem
      v-for="video in videos"
      :key="video.id"
      :video="video"
      :showAvatar="showAvatar"
      :setVideoRef="setVideoRef"
      :refreshContent="refreshContent"
      @play="$emit('play', video)"
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
import useOptionsMenu from "../composables/useOptionsMenu.js";


const props = defineProps({
  videos: Array,
  loading: Boolean,
  showAvatar: {
    type: Boolean,
    default: true
  },
  setVideoRef: Function,
  refreshContent: Function,
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
  'openModal',
]);

const { refreshContent } = useOptionsMenu(props.videos);

const {
  toggleOptions,
  toggleReadStatus,
  markReadBatch,
  downloadVideo,
  copyVideoLink,
  dislikeVideo,
} = useOptionsMenu(props.videos, refreshContent);



</script>

<style scoped>
/* 保持现有样式不变 */
</style>
