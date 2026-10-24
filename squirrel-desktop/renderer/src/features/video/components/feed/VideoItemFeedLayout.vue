<template>
  <VideoItemPlaybackControl :title="video.title" @activate="emit('activate')" />
  <VideoItemActions
    v-bind="actions"
    overlay
    class="video-item__controls"
    @toggle-like="emit('toggleLike')"
    @toggle-read="emit('toggleRead', $event)"
    @toggle-later="emit('toggleLater')"
  />
  <div class="video-item__presentation">
    <VideoItemThumbnail v-bind="thumbnail" variant="card" />
    <div class="video-item__headline">
      <span
        v-if="!actions.isRead"
        class="video-item__unread-dot"
        role="img"
        aria-label="未读"
      />
      <h3 class="video-item__title video-item__title--card">{{ video.title }}</h3>
    </div>
  </div>
  <VideoItemProfileMetadata
    v-bind="profile"
    class="video-item__controls video-item__meta-row"
    @open-profile="emit('openProfile', $event)"
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
