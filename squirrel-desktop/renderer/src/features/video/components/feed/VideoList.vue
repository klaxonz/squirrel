<template>
  <div ref="root" class="video-list" :class="`video-list--${presentation}`">
    <template v-if="videos.length > 0">
      <template v-if="grouped">
        <section
          v-for="group in videoGroups"
          :key="group.title"
          class="video-list__group"
        >
          <header class="video-list__group-header">
            <h3>{{ group.title }}</h3>
            <span>{{ group.videos.length }}</span>
          </header>
          <div :class="contentLayoutClass">
            <VideoItem
              v-for="video in group.videos"
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
        </section>
      </template>
      <div v-else :class="contentLayoutClass">
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
    </template>

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
import { useFeedGrouping } from '@/features/video/composables/useFeedGrouping'
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

const grouped = computed(() => props.presentation === 'workbench')
const feedItems = computed(() => props.videos)
const { videoGroups } = useFeedGrouping({ feedItems })

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
  /* Hug content start — no centered island on ultrawide. */
  margin-inline: 0;
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

/* Workbench list fills the media canvas as dense media rows. */
.video-list__workbench-list {
  display: flex;
  width: 100%;
  max-width: none;
  margin-inline: 0;
  flex-direction: column;
  gap: 0.5rem;
}

.video-list__group + .video-list__group {
  margin-top: var(--space-7);
}

.video-list__group-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
  border-bottom: 1px solid var(--app-hairline);
  margin-bottom: var(--space-3);
  padding-bottom: 0.45rem;
}

.video-list__group-header h3 {
  margin: 0;
  color: hsl(var(--foreground));
  font-family: var(--font-display);
  font-size: var(--app-text-base);
  font-weight: 600;
  letter-spacing: -0.02em;
}

.video-list__group-header span {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-2xs);
  font-variant-numeric: tabular-nums;
}
</style>
