<template>
  <div class="video-list-container relative max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8" ref="containerRef">
    <VirtualList
        class="scroller"
        :items="props.videos"
        :item-size="layout.itemSize"
        key-field="id"
        :buffer="BUFFER_PX"
        buffer-mode="px"
        @scroll="handleScroll"
        :gridItems="layout.gridItems"
        :prerender="PRERENDER_COUNT"
        anchor-mode="element"
        :range-change-throttle-ms="RANGE_CHANGE_THROTTLE_MS"
        :item-secondary-size="layout.itemSecondarySize"
        ref="virtualList"
    >
      <template #item="{ item: video, index }">
        <div class="grid-item">
          <VideoItem
              :video="video"
              :showAvatar="showAvatar"
              :showProgress="video.showProgress"
              :progress="video.progress"
              :index="index"
              :class="{ 'is-refreshing': refreshing }"
              @toggleOptions="$emit('toggleOptions', $event, video.id)"
              @goToSubscription="$emit('goToSubscription', $event)"
              @openModal="$emit('openModal', video)"
              @markReadBatch="handleMarkReadBatch"
          />
        </div>
      </template>
    </VirtualList>

    <!-- 加载更多指示器 -->
    <div v-if="props.loading" class="loading-indicator text-center py-4">
      <svg class="animate-spin h-5 w-5 text-gray-500 mx-auto" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <p class="mt-2">加载更多...</p>
    </div>

    <!-- 空状态提示 -->
    <div v-else-if="!props.loading && (!props.videos || props.videos.length === 0)" class="text-center py-8 text-sm text-gray-500">
      暂无内容
    </div>

  </div>
</template>

<script setup>
import {computed, ref} from 'vue';
import VirtualList from './VirtualList.vue';
import VideoItem from './VideoItem.vue';
import { useElementSize } from '../composables/useElementSize.js';

// Display/layout constants
const ASPECT_RATIO = 9 / 16;
const CARD_VERTICAL_EXTRA = 76; // non-thumbnail vertical space (title, paddings, etc.)
const BUFFER_PX = 400;
const PRERENDER_COUNT = 50;
const RANGE_CHANGE_THROTTLE_MS = 60;
const PRELOAD_ROWS = 3; // rows ahead of bottom to trigger loading

const props = defineProps({
  videos: Array,
  loading: Boolean,
  allLoaded: Boolean,
  showAvatar: Boolean,
  refreshing: {
    type: Boolean,
    default: false
  },
});

const emit = defineEmits([
  'toggleOptions',
  'goToSubscription',
  'openModal',
  'loadMore',
  'batchMarkAsRead',
  'markReadBatch'
]);

const containerRef = ref(null);
const { width: containerWidth } = useElementSize(containerRef);

const calculateGridItems = (width) => {
  if (width >= 1600) return 7;
  if (width >= 1400) return 6;
  if (width >= 1100) return 5;
  if (width >= 800) return 4;
  if (width >= 500) return 3;
  return 2;
};

// Unified layout computed to keep related values in sync
const layout = computed(() => {
  const width = containerWidth.value || 0;
  const gridItems = calculateGridItems(width);
  const itemSecondarySize = Math.floor(width / gridItems);
  const itemSize = Math.floor(itemSecondarySize * ASPECT_RATIO) + CARD_VERTICAL_EXTRA;
  return { gridItems, itemSecondarySize, itemSize };
});

const triggerThreshold = computed(() => layout.value.itemSize * layout.value.gridItems * PRELOAD_ROWS);

const shouldLoadMore = (scrollTop, clientHeight, scrollHeight) => {
  if (props.loading || props.allLoaded) return false;
  return (scrollHeight - scrollTop - clientHeight) < triggerThreshold.value;
};

const handleScroll = (event) => {
  const {scrollTop, clientHeight, scrollHeight} = event.target;
  // 增加预加载触发阈值，提前3行的高度开始加载，确保用户滚动时不需要等待
  if (shouldLoadMore(scrollTop, clientHeight, scrollHeight)) {
    emit('loadMore');
  }
};

const handleMarkReadBatch = (videoId, isRead, direction) => {
  emit('markReadBatch', videoId, isRead, direction);
};

const virtualList = ref(null);


defineExpose({
  scrollToTop: () => {
    virtualList.value?.container.scrollTo({ top: 0 });
  }
});

</script>

<style scoped>
.video-list-container {
  height: 100%;
  overflow-y: auto;
  margin: 0 auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.video-list-container::-webkit-scrollbar {
  display: none;
}

.scroller {
  height: 100%;
  overflow-y: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.scroller::-webkit-scrollbar {
  display: none;
}

.grid-item {
  width: 100%;
  padding: 4px;
  box-sizing: border-box;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.grid-item :deep(.video-item) {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.grid-item :deep(.video-thumbnail) {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.grid-item :deep(img) {
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  will-change: transform;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 刷新时对卡片添加轻量蒙层，避免闪白与突变感 */
.grid-item :deep(.video-item.is-refreshing)::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,0.06), rgba(255,255,255,0));
  animation: shimmer 1.2s infinite;
  pointer-events: none;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.loading-indicator, .text-center {
  height: 60px;
}
</style>
