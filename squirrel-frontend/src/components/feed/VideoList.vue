<template>
  <div class="video-list-container relative" ref="containerRef">
    <div v-if="props.loading && !hasVideos" class="video-list__state">
      <LoadingIndicator :loading="true" text="正在整理内容..." size="lg" />
    </div>

    <Card v-else-if="!props.loading && !hasVideos" class="video-list__empty">
      <CardContent class="video-list__empty-content">
        <p class="video-list__empty-eyebrow">空列表</p>
        <h3 class="video-list__empty-title">当前筛选下没有内容</h3>
        <p class="video-list__empty-copy">切换分类、站点或排序后再看。</p>
      </CardContent>
    </Card>

    <template v-else>
      <VirtualList
        class="scroller scrollbar-hide"
        :items="props.videos"
        :item-size="layout.itemSize"
        key-field="id"
        :buffer="BUFFER_PX"
        buffer-mode="px"
        :gridItems="layout.gridItems"
        :prerender="PRERENDER_COUNT"
        :range-change-throttle-ms="RANGE_CHANGE_THROTTLE_MS"
        :bottom-padding="80"
        ref="virtualList"
        @scroll="handleScroll"
      >
        <template #item="{ item: video }">
          <div class="grid-item">
            <VideoItem
              :video="video"
              :show-avatar="showAvatar"
              :sort-by="sortBy"
              :show-progress="video.showProgress"
              :progress="video.progress"
              :class="{ 'is-refreshing': refreshing }"
              @goToSubscription="$emit('goToSubscription', $event)"
              @openModal="$emit('openModal', video)"
            />
          </div>
        </template>
      </VirtualList>

      <div v-if="props.loading" class="video-list__loading-more">
        <LoadingIndicator :loading="true" text="继续加载中..." size="md" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Card, CardContent } from '@/components/ui/card'
import { useElementSize } from '@/composables/useElementSize'
import LoadingIndicator from './LoadingIndicator.vue'
import VideoItem from './VideoItem.vue'
import VirtualList from './VirtualList.vue'

const ASPECT_RATIO = 9 / 16
const GRID_ITEM_HORIZONTAL_PADDING = 10
const GRID_ITEM_VERTICAL_PADDING = 10
const CARD_INFO_HEIGHT = 92
const BUFFER_PX = 400
const PRERENDER_COUNT = 50
const RANGE_CHANGE_THROTTLE_MS = 60
const PRELOAD_ROWS = 3

const props = defineProps({
  videos: Array,
  loading: Boolean,
  allLoaded: Boolean,
  showAvatar: Boolean,
  sortBy: { type: String, default: 'publish_date' },
  refreshing: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits([
  'goToSubscription',
  'openModal',
  'loadMore',
  'batchMarkAsRead',
])

const containerRef = ref(null)
const virtualList = ref(null)
const { width: containerWidth } = useElementSize(containerRef)

const hasVideos = computed(() => Array.isArray(props.videos) && props.videos.length > 0)

const calculateGridItems = (width) => {
  if (width >= 2560) return 8
  if (width >= 1920) return 7
  if (width >= 1600) return 6
  if (width >= 1400) return 5
  if (width >= 1100) return 4
  if (width >= 800) return 3
  return 2
}

const layout = computed(() => {
  const width = containerWidth.value || 0
  const gridItems = calculateGridItems(width)
  const itemSecondarySize = Math.floor(width / gridItems)
  const cardWidth = Math.max(0, itemSecondarySize - GRID_ITEM_HORIZONTAL_PADDING)
  const thumbnailHeight = Math.floor(cardWidth * ASPECT_RATIO)
  const itemSize = thumbnailHeight + CARD_INFO_HEIGHT + GRID_ITEM_VERTICAL_PADDING

  return { gridItems, itemSize }
})

const triggerThreshold = computed(() => layout.value.itemSize * PRELOAD_ROWS)

const shouldLoadMore = (scrollTop, clientHeight, scrollHeight) => {
  if (props.loading || props.allLoaded) return false
  return (scrollHeight - scrollTop - clientHeight) < triggerThreshold.value
}

const handleScroll = (event) => {
  const { scrollTop, clientHeight, scrollHeight } = event.target
  if (shouldLoadMore(scrollTop, clientHeight, scrollHeight)) {
    emit('loadMore')
  }
}

defineExpose({
  scrollToTop: () => {
    virtualList.value?.scrollToOffset(0)
  },
})
</script>

<style scoped>
.video-list-container {
  height: 100%;
  overflow: hidden;
  margin: 0 auto;
  padding: 0 1rem 0.25rem;
  max-width: var(--container-max-width, 2560px);
}

.scroller {
  height: 100%;
  overflow-y: auto;
  padding-bottom: 1.25rem;
  box-sizing: border-box;
}

.grid-item {
  width: 100%;
  height: 100%;
  padding: 0.25rem;
  box-sizing: border-box;
}

.video-list__state,
.video-list__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: min(58vh, 32rem);
}

.video-list__empty {
  border-radius: calc(var(--radius-2xl) - 2px);
  border-color: hsl(var(--border) / 0.72);
  background: hsl(var(--card));
  box-shadow: var(--shadow-sm);
}

.video-list__empty-content {
  padding: 1.5rem 1rem;
  text-align: center;
}

.video-list__empty-eyebrow {
  margin: 0 0 0.4rem;
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: hsl(var(--muted-foreground));
}

.video-list__empty-title {
  margin: 0;
  font-size: clamp(1rem, 0.95rem + 0.2vw, 1.15rem);
  font-weight: 700;
  letter-spacing: -0.03em;
  color: hsl(var(--foreground));
}

.video-list__empty-copy {
  margin: 0.45rem 0 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.8rem;
}

.video-list__loading-more {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  padding-bottom: 0.2rem;
}

.grid-item :deep(.video-item.is-refreshing)::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, hsl(var(--background) / 0.32), transparent);
  animation: shimmer 1.2s infinite;
  pointer-events: none;
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }

  100% {
    transform: translateX(100%);
  }
}

@media (min-width: 640px) {
  .video-list-container {
    padding: 0 1.5rem 0.35rem;
  }
}

@media (min-width: 1024px) {
  .video-list-container {
    padding: 0 2rem 0.35rem;
  }
}

@media (max-width: 640px) {
  .grid-item {
    padding: 0.18rem;
  }

  .video-list__empty-content {
    padding: 1.35rem 0.9rem;
  }
}
</style>
