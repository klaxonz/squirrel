<template>
  <div class="video-list-container relative" ref="containerRef">
    <Transition name="fade-list" mode="out-in">
      <div v-if="props.loading && !hasVideos" key="skeleton" class="video-list-skeleton-grid">
        <div 
          v-for="i in layout.gridItems * 3" 
          :key="i" 
          class="grid-item"
          :style="{ width: `${100 / layout.gridItems}%` }"
        >
          <VideoSkeleton :delay="i * 100" />
        </div>
      </div>

      <div v-else-if="!props.loading && !hasVideos" key="empty" class="video-list-empty-minimal">
        <div class="empty-status">暂无内容</div>
        <div class="empty-copy">系统就绪 / 请尝试重置过滤条件</div>
      </div>

      <div v-else key="list" class="h-full w-full">
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
          <LoadingIndicator :loading="true" text="正在同步新数据" size="sm" />
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Card, CardContent } from '@/components/ui/card'
import { useElementSize } from '@/composables/useElementSize'
import LoadingIndicator from './LoadingIndicator.vue'
import VideoItem from './VideoItem.vue'
import VideoSkeleton from './VideoSkeleton.vue'
import VirtualList from './VirtualList.vue'

const ASPECT_RATIO = 9 / 16
const GRID_ITEM_HORIZONTAL_PADDING = 16
const GRID_ITEM_VERTICAL_PADDING = 24
const CARD_INFO_HEIGHT = 70
const BUFFER_PX = 1200
const PRERENDER_COUNT = 40
const RANGE_CHANGE_THROTTLE_MS = 30
const PRELOAD_ROWS = 4

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
  width: 100%;
  position: absolute;
  inset: 0;
  overflow: hidden;
  margin: 0;
  padding: 0 2rem;
  max-width: 100%;
}

.scroller {
  height: 100%;
  overflow-y: auto;
  padding-bottom: 5rem;
  box-sizing: border-box;
}

.grid-item {
  width: 100%;
  height: 100%;
  padding: 0.5rem;
  box-sizing: border-box;
}

.video-list-skeleton-grid {
  display: flex;
  flex-wrap: wrap;
  width: 100%;
  padding-top: 0.5rem;
}

.fade-list-enter-active,
.fade-list-leave-active {
  transition: opacity 0.4s ease;
}

.fade-list-enter-from,
.fade-list-leave-to {
  opacity: 0;
}

.video-list-empty-minimal {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 60vh;
  gap: 1rem;
}

.empty-status {
  font-family: 'Courier New', Courier, monospace;
  font-size: 1.5rem;
  font-weight: 800;
  letter-spacing: -0.05em;
  color: rgba(255, 255, 255, 0.05);
}

.empty-copy {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.6rem;
  letter-spacing: 0.4em;
  color: rgba(255, 255, 255, 0.15);
  text-transform: uppercase;
}

.video-list__loading-more {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  padding: 2rem 0 1rem;
  background: linear-gradient(to top, hsl(var(--background)) 20%, transparent 100%);
  z-index: 20;
}

.grid-item :deep(.video-item.is-refreshing)::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.05), transparent);
  animation: shimmer 1.5s infinite;
  pointer-events: none;
  z-index: 10;
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
