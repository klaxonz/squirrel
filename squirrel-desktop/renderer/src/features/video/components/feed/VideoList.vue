<template>
  <div ref="root" class="video-list" :class="`video-list--${presentation}`">
    <div
      v-if="videos.length > 0"
      :class="contentLayoutClass"
    >
      <VideoItem
        v-for="video in videos"
        :key="video.id"
        :video="video"
        :show-avatar="showAvatar"
        :sort-by="sortBy"
        :layout="uiStore.viewMode"
        :appearance="presentation === 'workbench' ? 'workbench' : 'default'"
        @goToProfile="emit('goToProfile', $event)"
        @goToSubscription="emit('goToSubscription', $event)"
        @openModal="emit('openModal', video)"
      />
    </div>

    <div v-if="loading && !refreshing" :class="loadingLayoutClass">
      <VideoSkeleton
        v-for="index in skeletonCount"
        :key="index"
        :delay="(index - 1) * 40"
        :layout="uiStore.viewMode"
        :appearance="presentation === 'workbench' ? 'workbench' : 'default'"
      />
    </div>

    <div v-if="!loading && videos.length === 0" class="app-page-empty">
      <AppEmptyState variant="plain" icon="inbox" title="没有符合条件的视频" copy="调整筛选条件或搜索关键词后再试。" />
    </div>

    <div ref="loadMoreTrigger" class="h-20 w-full" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import VideoItem from './VideoItem.vue'
import VideoSkeleton from './VideoSkeleton.vue'
import { useUIStore } from '@/shared/stores/ui'
import { useInfiniteScrollSentinel } from '@/shared/composables/useInfiniteScrollSentinel'
import { useSkeletonCount } from '@/features/video/composables/useSkeletonCount'
import type { VideoListItem, VideoProfile } from '@/features/video/types/video'

const uiStore = useUIStore()

const props = withDefaults(defineProps<{
  videos: VideoListItem[]
  loading: boolean
  allLoaded: boolean
  showAvatar: boolean
  sortBy?: string
  refreshing: boolean
  presentation?: 'standard' | 'workbench'
}>(), {
  presentation: 'standard',
})

const emit = defineEmits<{
  goToProfile: [profile: VideoProfile]
  goToSubscription: [id: string | number | null | undefined]
  openModal: [video: VideoListItem]
  loadMore: []
}>()

const loadMoreTrigger = ref<HTMLElement | null>(null)
const densityMinWidth = computed(() => {
  if (uiStore.videoDensity === 'compact') return 224
  if (uiStore.videoDensity === 'large') return 352
  return 280
})

const workbenchGridClass = computed(() => [
  'video-list__workbench-grid',
  `is-${uiStore.videoDensity}`,
])

const contentLayoutClass = computed(() => {
  if (props.presentation === 'workbench') {
    return uiStore.viewMode === 'grid' ? workbenchGridClass.value : 'video-list__workbench-list'
  }
  return uiStore.viewMode === 'grid' ? 'app-video-grid' : 'video-list__list'
})

const loadingLayoutClass = computed(() => {
  if (props.presentation === 'workbench') {
    return uiStore.viewMode === 'grid' ? workbenchGridClass.value : 'video-list__workbench-list'
  }
  return uiStore.viewMode === 'grid' ? 'app-video-grid' : 'video-list__list'
})

const { count: skeletonCount, attachRef: root } = useSkeletonCount({
  minCardWidth: computed(() => (uiStore.viewMode === 'grid' ? densityMinWidth.value : Number.MAX_SAFE_INTEGER)),
  gap: 16,
  cardHeight: computed(() => (uiStore.viewMode === 'grid' ? 220 : 140)),
})

useInfiniteScrollSentinel({
  sentinel: loadMoreTrigger,
  onIntersect: () => {
    if (!props.loading && !props.allLoaded) emit('loadMore')
  },
  rootMargin: '600px',
})
</script>

<style scoped>
.video-list {
  width: 100%;
}

.video-list__list {
  display: flex;
  max-width: var(--app-content-feed-max);
  margin-inline: auto;
  flex-direction: column;
  gap: 0.75rem;
}

.video-list__workbench-grid {
  --video-canvas-min: 15.5rem;
  display: grid;
  width: 100%;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, var(--video-canvas-min)), 1fr));
  align-items: start;
  gap: 1.25rem 1rem;
}

.video-list__workbench-grid.is-compact {
  --video-canvas-min: 13rem;
  gap: 1rem 0.75rem;
}

.video-list__workbench-grid.is-large {
  --video-canvas-min: 18rem;
  gap: 1.5rem 1.25rem;
}

/* Reddit feed: discrete white cards with gap, not stacked hairlines. */
.video-list__workbench-list {
  display: flex;
  max-width: var(--app-content-feed-max);
  margin-inline: auto;
  flex-direction: column;
  gap: 0.75rem;
}
</style>
