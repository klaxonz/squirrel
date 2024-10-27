<template>
  <div class="virtual-list" ref="virtualList" style="height: 100%; overflow-y: auto;">
    <div class="virtual-list-inner" :style="{ height: totalHeight + 'px' }">
      <div 
        class="grid grid-cols-6 gap-4" 
        :style="{ transform: `translateY(${offsetY}px)` }"
      >
        <VideoItem
          v-for="video in visibleVideos"
          :key="video.id"
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
    </div>
  </div>
</template>

<script setup>
import VideoItem from './VideoItem.vue';
import useOptionsMenu from "../composables/useOptionsMenu.js";
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';

const virtualList = ref(null);
const rowHeight = ref(250); // Set an initial estimated height
const columnsPerRow = 6;
const visibleCount = ref(0);
const startIndex = ref(0);
const offsetY = ref(0);

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

const totalHeight = computed(() => Math.ceil(props.videos.length / columnsPerRow) * rowHeight.value);

const visibleVideos = computed(() => {
  const bufferSize = 2; // Number of extra rows to render above and below
  const start = Math.max(0, (startIndex.value - bufferSize) * columnsPerRow);
  const end = Math.min(props.videos.length, (startIndex.value + visibleCount.value + bufferSize) * columnsPerRow);
  return props.videos.slice(start, end);
});

const updateVisibleVideos = () => {
  if (!virtualList.value) return;
  const scrollTop = virtualList.value.scrollTop;
  startIndex.value = Math.floor(scrollTop / rowHeight.value);
  visibleCount.value = Math.ceil(virtualList.value.clientHeight / rowHeight.value) + 1;
  offsetY.value = Math.max(0, (startIndex.value - 2) * rowHeight.value); // Subtract 2 rows for upward scrolling buffer

  // Check if we need to load more videos
  if (scrollTop + virtualList.value.clientHeight >= totalHeight.value - rowHeight.value * 4 && !props.loading && !props.allLoaded) {
    emit('loadMore');
  }
};

const handleScroll = () => {
  requestAnimationFrame(updateVisibleVideos);
};

const updateRowHeight = () => {
  nextTick(() => {
    const firstItem = virtualList.value.querySelector('.grid > *');
    if (firstItem) {
      const newRowHeight = firstItem.offsetHeight + 16; // 16 is the gap
      if (newRowHeight !== rowHeight.value) {
        rowHeight.value = newRowHeight;
        updateVisibleVideos();
      }
    }
  });
};

onMounted(() => {
  updateRowHeight();
  updateVisibleVideos();
  virtualList.value.addEventListener('scroll', handleScroll);
});

onUnmounted(() => {
  virtualList.value.removeEventListener('scroll', handleScroll);
});

watch(() => props.videos.length, () => {
  updateRowHeight();
  updateVisibleVideos();
});
</script>

<style scoped>
/* 保持现有样式不变 */
</style>
