<template>
  <VideoItemPlaybackControl :title="video.title" @activate="emit('activate')" />
  <div class="video-item__lead-media">
    <VideoItemThumbnail v-bind="thumbnail" variant="card" />
    <span v-if="!actions.isRead" class="video-item__lead-stamp">未读</span>
  </div>
  <div class="video-item__lead-body">
    <span class="video-item__lead-eyebrow">今日精选</span>
    <h3 class="video-item__title video-item__title--lead">{{ video.title }}</h3>
    <VideoItemProfileMetadata
      v-bind="profile"
      class="video-item__controls"
      @open-profile="emit('openProfile', $event)"
    />
    <VideoItemActions
      v-bind="actions"
      class="video-item__lead-actions video-item__controls"
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
