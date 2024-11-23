<template>
  <div class="video-list-container relative" ref="containerRef">
    <RecycleScroller
      class="scroller"
      :items="props.videos"
      :item-size="computedItemSize"
      key-field="id"
      :buffer="400"
      @scroll="handleScroll"
      :gridItems="computedGridItems"
      :prerender="30"
      :item-secondary-size="computedItemSecondarySize"
    >
      <template #default="{ item: video }">
        <div class="grid-item">
          <VideoItem
            :video="video"
            :isSelected="selectedVideos.includes(video.id)"
            @toggleSelection="toggleVideoSelection"
            :isChannelPage="isChannelPage"
            :showAvatar="showAvatar"
            :refreshContent="refreshContent"
            :showProgress="video.showProgress"
            :progress="video.progress"
            @toggleOptions="$emit('toggleOptions', $event, video.id)"
            @goToChannel="$emit('goToChannel', $event)"
            @openModal="$emit('openModal', video)"
            @markReadBatch="handleMarkReadBatch"
          />
        </div>
      </template>
    </RecycleScroller>
    
    <!-- 批量操作浮动按钮 -->
    <div v-if="selectedVideos.length > 0" class="fixed bottom-4 right-4 z-50">
      <button @click="batchMarkAsRead" class="bg-blue-500 text-white px-4 py-2 rounded-full shadow-lg mr-2">
        标记为已读 ({{ selectedVideos.length }})
      </button>
      <button @click="clearSelection" class="bg-gray-500 text-white px-4 py-2 rounded-full shadow-lg">
        取消选择
      </button>
    </div>

    <!-- 加载更多指示器 -->
    <div v-if="props.loading" class="loading-indicator text-center py-4">
      <svg class="animate-spin h-5 w-5 text-gray-500 mx-auto" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
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
import { ref, onMounted, watch, computed, onUnmounted, provide, nextTick } from 'vue';
import { RecycleScroller } from 'vue-virtual-scroller';
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css';
import VideoItem from './VideoItem.vue';

const props = defineProps({
  videos: Array,
  loading: Boolean,
  allLoaded: Boolean,
  showAvatar: Boolean,
  isChannelPage: Boolean,
  refreshContent: Function,
});

const emit = defineEmits([
  'toggleOptions',
  'goToChannel',
  'openModal',
  'loadMore',
  'batchMarkAsRead',
  'markReadBatch'
]);

const containerRef = ref(null);
const containerWidth = ref(0);
const sidePadding = 16;

const updateContainerWidth = () => {
  if (containerRef.value) {
    requestAnimationFrame(() => {
      containerWidth.value = containerRef.value.offsetWidth - (sidePadding * 2);
    });
  }
};

onMounted(() => {
  updateContainerWidth();
  window.addEventListener('resize', updateContainerWidth);
  
  const resizeObserver = new ResizeObserver(() => {
    updateContainerWidth();
    checkInitialContent();
  });
  
  if (containerRef.value) {
    resizeObserver.observe(containerRef.value);
  }
  
  nextTick(() => {
    checkInitialContent();
  });
  
  onUnmounted(() => {
    window.removeEventListener('resize', updateContainerWidth);
    resizeObserver.disconnect();
  });
});

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
  return Math.floor(availableWidth / computedGridItems.value);
});

const computedItemSize = computed(() => {
  return Math.floor(computedItemSecondarySize.value * (9 / 16) + 76);
});

const selectedVideos = ref([]);
const isSelectionMode = computed(() => selectedVideos.value.length > 0);
provide('isSelectionMode', isSelectionMode);

const toggleVideoSelection = (videoId) => {
  const index = selectedVideos.value.indexOf(videoId);
  if (index === -1) {
    selectedVideos.value.push(videoId);
  } else {
    selectedVideos.value.splice(index, 1);
  }
};

const batchMarkAsRead = () => {
  // 实现批量标记为已读的逻辑
  emit('batchMarkAsRead', selectedVideos.value);
  clearSelection();
};

const clearSelection = () => {
  selectedVideos.value = [];
};

const handleScroll = (event) => {
  const { scrollTop, clientHeight, scrollHeight } = event.target;
  if (scrollHeight - scrollTop - clientHeight < computedItemSize.value * 2 && !props.loading && !props.allLoaded) {
    emit('loadMore');
  }
};

const handleMarkReadBatch = (videoId, isRead, direction) => {
  emit('markReadBatch', videoId, isRead, direction);
};

const checkInitialContent = () => {
  if (!containerRef.value) return;
  
  const container = containerRef.value;
  const scroller = container.querySelector('.scroller');
  if (!scroller) return;

  // 如果内容高度小于容器高度，且还有更多内容可以加载，则触发加载更多
  if (scroller.scrollHeight <= scroller.clientHeight && !props.loading && !props.allLoaded) {
    emit('loadMore');
  }
};

watch(() => props.videos.length, () => {
  nextTick(() => {
    updateContainerWidth();
    checkInitialContent();
  });
});
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
