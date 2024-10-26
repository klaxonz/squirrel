<template>
  <div class="grid grid-cols-5 gap-4">
    <VideoItem
      v-for="video in videos"
      :key="video.id"
      :video="video"
      :isChannelPage="isChannelPage"
      :activeTab="activeTab"
      :showAvatar="showAvatar"
      :setVideoRef="setVideoRef"
      :refreshContent="refreshContent"
      @toggleOptions="$emit('toggleOptions', $event, video.id)"
      @goToChannel="$emit('goToChannel', video.channel_id)"
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
  isChannelPage: Boolean,
  activeTab: String,
  setVideoRef: Function,
  refreshContent: Function,
});
defineEmits([
  'toggleOptions',
  'goToChannel',
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
