<template>
  <VideoItemPlaybackControl :title="video.title" @activate="emit('activate')" />
  <header class="video-item__top video-item__controls">
    <VideoItemProfileMetadata v-bind="profile" @open-profile="emit('openProfile', $event)" />
    <VideoItemActions v-bind="actions" compact @toggle-later="emit('toggleLater')" />
  </header>
  <div class="video-item__presentation">
    <h3 class="video-item__title video-item__title--card">{{ video.title }}</h3>
    <VideoItemThumbnail v-bind="thumbnail" variant="card" />
  </div>
  <VideoItemActions
    v-bind="actions"
    class="video-item__controls"
    @toggle-like="emit('toggleLike')"
    @toggle-read="emit('toggleRead', $event)"
    @toggle-later="emit('toggleLater')"
  />
</template>

<script setup lang="ts">
import type { VideoListItem, VideoProfile } from '@/features/video/types/video'
import VideoItemActions from './VideoItemActions.vue'
import VideoItemPlaybackControl from './VideoItemPlaybackControl.vue'
import VideoItemProfileMetadata from './VideoItemProfileMetadata.vue'
import VideoItemThumbnail from './VideoItemThumbnail.vue'

defineProps<{
  video: VideoListItem
  thumbnail: InstanceType<typeof VideoItemThumbnail>['$props']
  profile: InstanceType<typeof VideoItemProfileMetadata>['$props']
  actions: InstanceType<typeof VideoItemActions>['$props']
}>()
const emit = defineEmits<{
  activate: []
  openProfile: [profile: VideoProfile]
  toggleLike: []
  toggleRead: [markRead: boolean]
  toggleLater: []
}>()
</script>
