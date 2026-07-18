<template>
  <section v-if="items.length > 0 || loading || loadError" class="featured-workspace">
    <FeedRailHeader
      title="精选推荐"
      view-more
      @view-more="$emit('viewMore')"
    />

    <div v-if="loadError && !loading && items.length === 0" class="app-page-empty app-page-empty--compact">
      <AppEmptyState variant="error" title="推荐内容加载失败" :copy="loadError">
        <template #actions>
          <Button size="sm" @click="load">重试</Button>
        </template>
      </AppEmptyState>
    </div>

    <div v-else class="featured-workspace__grid app-video-grid app-video-grid--compact">
      <RecommendationSkeleton v-if="loading && items.length === 0" :count="6" />
      <VideoItem
        v-for="video in items"
        :key="video.id"
        :video="video"
        show-duration
        thumbnail-status="none"
        @openModal="$emit('openModal', video)"
        @goToProfile="(profile) => $emit('goToProfile', profile)"
        @goToSubscription="(id) => $emit('goToSubscription', id)"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getFeaturedVideos } from '@/shared/api/video'
import type { VideoListItem, VideoProfile } from '@/features/video/types/video'
import { errorMessage } from '@/shared/lib/errorMessage'
import { Logger } from '@/shared/lib/logger'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import { Button } from '@/shared/ui/button'
import FeedRailHeader from '@/features/video/components/feed/FeedRailHeader.vue'
import VideoItem from '@/features/video/components/feed/VideoItem.vue'
import RecommendationSkeleton from '@/features/video/components/feed/RecommendationSkeleton.vue'

defineEmits<{
  openModal: [video: VideoListItem]
  goToProfile: [profile: VideoProfile]
  goToSubscription: [id: number | string | null | undefined]
  viewMore: []
}>()

const items = ref<VideoListItem[]>([])
const loading = ref(false)
const loadError = ref('')
const load = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const data = await getFeaturedVideos()
    items.value = Array.isArray(data) ? data.slice(0, 12) : []
  } catch (e) {
    Logger.warn('Failed to load featured videos rail:', e)
    items.value = []
    loadError.value = errorMessage(e, '推荐内容加载失败，请重试')
  } finally {
    loading.value = false
  }
}

onMounted(load)

defineExpose({ refresh: load })
</script>

<style scoped>
.featured-workspace {
  min-width: 0;
  padding-top: var(--space-5);
  border-top: 1px solid var(--app-hairline);
}

.featured-workspace__grid {
  --app-grid-min: 15.5rem;
  align-items: start;
}

.featured-workspace__grid :deep(.app-video-rail-card) {
  width: auto;
  min-width: 0;
  flex: initial;
}
</style>
