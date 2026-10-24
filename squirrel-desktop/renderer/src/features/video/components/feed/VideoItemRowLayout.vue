<template>
  <VideoItemPlaybackControl :title="video.title" @activate="emit('activate')" />

  <div class="video-item__row-media">
    <VideoItemThumbnail v-bind="thumbnail" variant="row" />
    <VideoItemActions
      v-bind="actions"
      overlay
      class="video-item__controls"
      @toggle-like="emit('toggleLike')"
      @toggle-read="emit('toggleRead', $event)"
      @toggle-later="emit('toggleLater')"
    />
  </div>

  <div class="video-item__row-content">
    <h3 class="video-item__title video-item__title--card">{{ video.title }}</h3>
    <VideoItemProfileMetadata
      v-bind="profile"
      grid
      class="video-item__controls"
      @open-profile="emit('openProfile', $event)"
    />
  </div>
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
