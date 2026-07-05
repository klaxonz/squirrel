<template>
  <div ref="root" class="w-full">
    <!-- List/Grid Container -->
    <div v-if="videos.length > 0"
         :class="uiStore.viewMode === 'grid'
           ? 'app-video-grid app-page-section--grid'
           : 'app-page-section--list'">
      <VideoItem
        v-for="video in videos"
        :key="video.id"
        :video="video"
        :show-avatar="showAvatar"
        :sort-by="sortBy"
        :layout="uiStore.viewMode"
        @goToSubscription="$emit('goToSubscription', $event)"
        @openModal="$emit('openModal', video)"
      />
    </div>

    <!-- Loading State: only the initial load shows the skeleton grid.
         On tab switch / refresh / load-more, `videos` already holds
         content and `refreshing` is true — we must NOT render the
         skeleton block alongside the stale items. -->
    <div v-if="loading && !refreshing"
         :class="uiStore.viewMode === 'grid'
           ? 'app-video-grid app-page-section--grid'
           : 'app-page-section--list'">
      <VideoSkeleton v-for="i in skeletonCount" :key="i" :delay="(i - 1) * 50" :layout="uiStore.viewMode" />
    </div>

    <!-- Empty State -->
    <div v-if="!loading && videos.length === 0" class="app-page-empty">
      <AppEmptyState variant="plain" icon="inbox" title="未找到内容" copy="请调整筛选条件或搜索关键词后再试。" />
    </div>

    <!-- Infinite Scroll Trigger -->
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
import type { VideoListItem } from '@/features/video/types/video'

const uiStore = useUIStore()

const props = defineProps<{
  videos: VideoListItem[]
  loading: boolean
  allLoaded: boolean
  showAvatar: boolean
  sortBy?: string
  refreshing: boolean
}>()

const emit = defineEmits(['goToSubscription', 'openModal', 'loadMore'])

const loadMoreTrigger = ref<HTMLElement | null>(null)

// Skeleton column count is derived from the same auto-fill formula the CSS grid
// uses (minCardWidth + gap → column count), so it stays in sync with the real
// `.app-video-grid` without a hand-mirrored breakpoint table. List mode forces
// a single column by setting an impossibly large min card width.
const { count: skeletonCount, attachRef: root } = useSkeletonCount({
  minCardWidth: computed(() => (uiStore.viewMode === 'grid' ? 280 : Number.MAX_SAFE_INTEGER)),
  gap: 24, // matches --app-video-grid-gap (1.5rem)
  cardHeight: computed(() => (uiStore.viewMode === 'grid' ? 220 : 140)),
})

// ponytail: the sentinel IntersectionObserver + mount/unmount lifecycle lives
// in useInfiniteScrollSentinel (deduped from 3 video-feed components). The
// loading/allLoaded guards stay in the callback since they're component-specific.
useInfiniteScrollSentinel({
  sentinel: loadMoreTrigger,
  onIntersect: () => {
    if (!props.loading && !props.allLoaded) emit('loadMore')
  },
  rootMargin: '600px',
})

</script>

<style scoped>
</style>
