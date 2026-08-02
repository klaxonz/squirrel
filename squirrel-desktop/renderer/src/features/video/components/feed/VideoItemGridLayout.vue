<template>
  <VideoItemPlaybackControl :title="video.title" @activate="emit('activate')" />
  <div class="video-item__presentation">
    <VideoItemThumbnail v-bind="thumbnail" variant="grid" />
    <h3 class="video-item__title video-item__title--grid">{{ video.title }}</h3>
  </div>
  <div class="video-item__body video-item__controls">
    <VideoItemProfileMetadata v-bind="profile" grid @open-profile="emit('openProfile', $event)" />
  </div>
</template>

<script setup lang="ts">
import type { VideoListItem, VideoProfile } from '@/features/video/types/video'
import VideoItemPlaybackControl from './VideoItemPlaybackControl.vue'
import VideoItemProfileMetadata from './VideoItemProfileMetadata.vue'
import VideoItemThumbnail from './VideoItemThumbnail.vue'

defineProps<{
  video: VideoListItem
  thumbnail: InstanceType<typeof VideoItemThumbnail>['$props']
  profile: InstanceType<typeof VideoItemProfileMetadata>['$props']
}>()
const emit = defineEmits<{ activate: []; openProfile: [profile: VideoProfile] }>()
</script>
