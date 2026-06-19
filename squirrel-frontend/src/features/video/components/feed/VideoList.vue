<template>
  <div ref="root" class="w-full">
    <!-- List/Grid Container -->
    <div v-if="videos.length > 0"
         :class="uiStore.viewMode === 'grid'
           ? 'grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6 gap-6 p-6'
           : 'flex flex-col gap-4 p-6 max-w-4xl mx-auto'">
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
           ? 'grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6 gap-6 p-6'
           : 'flex flex-col gap-4 p-6 max-w-4xl mx-auto'">
      <VideoSkeleton v-for="i in skeletonCount" :key="i" :delay="(i - 1) * 50" :layout="uiStore.viewMode" />
    </div>

    <!-- Empty State -->
    <div v-if="!loading && videos.length === 0" class="min-h-[60vh] p-10">
      <AppEmptyState variant="plain" icon="inbox" title="未找到内容" copy="请调整筛选条件或搜索关键词后再试。" />
    </div>

    <!-- Infinite Scroll Trigger -->
    <div ref="loadMoreTrigger" class="h-20 w-full" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import VideoItem from './VideoItem.vue'
import VideoSkeleton from './VideoSkeleton.vue'
import { useUIStore } from '@/shared/stores/ui'
import { getMainScrollRoot } from '@/shared/composables/useMainScrollRoot'
import { useSkeletonCount, type GridBreakpoint } from '@/features/video/composables/useSkeletonCount'
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
let observer: IntersectionObserver | null = null

// --- Adaptive skeleton count ----------------------------------------------
// Breakpoints must mirror the grid classes below:
// `grid-cols-1 md:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6`
const GRID_BREAKPOINTS: GridBreakpoint[] = [
  [1920, 6], // 3xl
  [1536, 5], // 2xl
  [1024, 4], // lg
  [768, 3],  // md
  [0, 1],    // base
]
// List mode is always a single column.
const LIST_BREAKPOINTS: GridBreakpoint[] = [[0, 1]]

const { count: skeletonCount, attachRef: root } = useSkeletonCount({
  // Layout swaps between grid and list depending on the toolbar view mode.
  breakpoints: computed(() =>
    uiStore.viewMode === 'grid' ? GRID_BREAKPOINTS : LIST_BREAKPOINTS,
  ),
  cardHeight: computed(() => (uiStore.viewMode === 'grid' ? 220 : 140)),
  rowGap: 24, // matches `gap-6` (1.5rem ≈ 24px)
})

onMounted(() => {
  // Use the app's primary scroll container as the observer root so the sentinel
  // triggers against the real scrolling viewport, not the window.
  const scrollRoot = getMainScrollRoot()

  observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && !props.loading && !props.allLoaded) {
      emit('loadMore')
    }
  }, {
    root: scrollRoot,
    rootMargin: '600px'
  })

  if (loadMoreTrigger.value) observer.observe(loadMoreTrigger.value)
})

onUnmounted(() => observer?.disconnect())
</script>

<style scoped>
</style>
