<template>
  <div class="video-list-container relative" ref="containerRef">
    <RecycleScroller
        class="scroller"
        :items="props.videos"
        :item-size="computedItemSize"
        key-field="id"
        :buffer="200"
        @scroll="handleScroll"
        :gridItems="computedGridItems"
        :prerender="30"
        :item-secondary-size="computedItemSecondarySize"
    >
      <template #default="{ item: video }">
        <div class="grid-item">
          <VideoItem
              :video="video"
              :showAvatar="showAvatar"
              :showProgress="video.showProgress"
              :progress="video.progress"
              @toggleOptions="$emit('toggleOptions', $event, video.id)"
              @goToSubscription="$emit('goToSubscription', $event)"
              @openModal="$emit('openModal', video)"
              @markReadBatch="handleMarkReadBatch"
          />
        </div>
      </template>
    </RecycleScroller>

    <!-- 加载更多指示器 -->
    <div v-if="props.loading" class="loading-indicator text-center py-4">
      <svg class="animate-spin h-5 w-5 text-gray-500 mx-auto" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <p class="mt-2">加载更多...</p>
    </div>

    <!-- 加载完成状态 -->
    <div v-if="props.allLoaded && !props.loading" class="text-center py-4">
      <p>没有更多视频了</p>
    </div>
  </div>
</template>

<script setup>
import {computed, onMounted, ref, inject, onUnmounted, onActivated} from 'vue';
import {RecycleScroller} from 'vue-virtual-scroller';
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css';
import VideoItem from './VideoItem.vue';

const props = defineProps({
  videos: Array,
  loading: Boolean,
  allLoaded: Boolean,
  showAvatar: Boolean,
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
const containerWidth = ref(0);

const emitter = inject('emitter');

onMounted(() => {
  updateContainerWidth();
  
  // 监听侧边栏状态变化
  emitter.on('sidebarStateChanged', updateContainerWidth);
  // 监听窗口大小变化
  window.addEventListener('resize', updateContainerWidth);

});

// 在组件卸载时清理事件监听
onUnmounted(() => {
  emitter.off('sidebarStateChanged', updateContainerWidth);
  emitter.off('reloadContent');
  window.removeEventListener('resize', updateContainerWidth);
});

onActivated(() => {
    updateContainerWidth();
})

// 优化 updateContainerWidth，添加防抖
const updateContainerWidth = (() => {
  let timer = null;
  return () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      if (containerRef.value) {
        requestAnimationFrame(() => {
          containerWidth.value = containerRef.value.offsetWidth;
        });
      }
    }, 100);
  };
})();

const computedGridItems = computed(() => {
  const width = containerWidth.value;
  if (width >= 1700) return 7;
  if (width >= 1400) return 6;
  if (width >= 1100) return 5;
  if (width >= 800) return 4;
  if (width >= 500) return 3;
  return 2;
});

const computedItemSecondarySize = computed(() => {
  const availableWidth = containerWidth.value;
  return Math.floor((availableWidth) / computedGridItems.value);
});

const computedItemSize = computed(() => {
  return Math.floor(computedItemSecondarySize.value * (9 / 16)) + 76;
});

const handleScroll = (event) => {
  const {scrollTop, clientHeight, scrollHeight} = event.target;
  if (scrollHeight - scrollTop - clientHeight < computedItemSize.value * 2 && !props.loading && !props.allLoaded) {
    emit('loadMore');
  }
};

const handleMarkReadBatch = (videoId, isRead, direction) => {
  emit('markReadBatch', videoId, isRead, direction);
};

</script>

<style scoped>
.video-list-container {
  height: 100%;
  overflow: hidden;
  margin: 0 auto;
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
  padding: 8px;
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

.loading-indicator, .text-center {
  height: 60px;
}
</style>
