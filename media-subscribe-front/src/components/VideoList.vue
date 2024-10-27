<template>
  <div class="video-list-container" ref="containerRef">
    <RecycleScroller
      class="scroller"
      :items="props.videos"
      :item-size="computedItemSize"
      key-field="id"
      :buffer="400"
      @scroll="handleScroll"
      :gridItems="computedGridItems"
      :prerender="20"
      :item-secondary-size="computedItemSecondarySize"
    >
      <template #default="{ item: video }">
        <div class="grid-item">
          <VideoItem
            :video="video"
            :isChannelPage="isChannelPage"
            :activeTab="activeTab"
            :showAvatar="showAvatar"
            :setVideoRef="setVideoRef"
            :refreshContent="refreshContent"
            @toggleOptions="$emit('toggleOptions', $event, video.id)"
            @goToChannel="$emit('goToChannel', video.channel_id)"
            @openModal="$emit('openModal', video)"
          />
        </div>
      </template>
    </RecycleScroller>
    
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
import { ref, onMounted, watch, computed, onUnmounted } from 'vue';
import { RecycleScroller } from 'vue-virtual-scroller';
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css';
import VideoItem from './VideoItem.vue';

const props = defineProps({
  videos: Array,
  loading: Boolean,
  allLoaded: Boolean,
  showAvatar: Boolean,
  isChannelPage: Boolean,
  activeTab: String,
  setVideoRef: Function,
  refreshContent: Function,
});

const emit = defineEmits([
  'toggleOptions',
  'goToChannel',
  'openModal',
  'loadMore',
]);

const containerRef = ref(null);
const containerWidth = ref(0);
const sidePadding = 16;

const updateContainerWidth = () => {
  if (containerRef.value) {
    containerWidth.value = containerRef.value.offsetWidth - (sidePadding * 2);
  }
};

onMounted(() => {
  updateContainerWidth();
  window.addEventListener('resize', updateContainerWidth);
});

onUnmounted(() => {
  window.removeEventListener('resize', updateContainerWidth);
});

const computedGridItems = computed(() => {
  const width = containerWidth.value;
  if (width >= 1700) return 6;
  if (width >= 1400) return 5;
  if (width >= 1100) return 4;
  if (width >= 800) return 3;
  if (width >= 500) return 2;
  return 1;
});

const computedItemSecondarySize = computed(() => {
  const availableWidth = containerWidth.value;
  return Math.floor(availableWidth / computedGridItems.value);
});

const computedItemSize = computed(() => {
  return Math.floor(computedItemSecondarySize.value * (9 / 16) + 70);
});



const handleScroll = (event) => {
  const { scrollTop, clientHeight, scrollHeight } = event.target;
  if (scrollHeight - scrollTop - clientHeight < computedItemSize.value * 2 && !props.loading && !props.allLoaded) {
    emit('loadMore');
  }
};

watch(() => props.videos.length, updateContainerWidth);
</script>

<style scoped>
.video-list-container {
  height: 100%;
  overflow: hidden;
  margin: 0 auto;
  padding: 0 v-bind(sidePadding + 'px');
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

.loading-indicator, .text-center {
  height: 60px;
}
</style>
