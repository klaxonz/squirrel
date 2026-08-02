<template>
  <VideoItemPlaybackControl :title="video.title" @activate="emit('activate')" />
  <div class="video-item__presentation video-item__row-thumbnail">
    <VideoItemThumbnail v-bind="thumbnail" variant="row" />
  </div>
  <div class="video-item__row-body">
    <header class="video-item__top video-item__top--row video-item__controls">
      <VideoItemProfileMetadata v-bind="profile" @open-profile="emit('openProfile', $event)" />
      <VideoItemActions v-bind="actions" compact @toggle-later="emit('toggleLater')" />
    </header>
    <h3 class="video-item__title video-item__title--row video-item__presentation">{{ video.title }}</h3>
    <VideoItemActions
      v-bind="actions"
      row
      class="video-item__controls"
      @toggle-like="emit('toggleLike')"
      @toggle-read="emit('toggleRead', $event)"
      @toggle-later="emit('toggleLater')"
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
