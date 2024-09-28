<template>
  <div class="video-waterfall" ref="waterfall">
    <VideoItem
      v-for="video in videos"
      :key="video.id"
      :video="video"
      :showAvatar="showAvatar"
      @play="$emit('play', video)"
      :setVideoRef="setVideoRef"
      @videoPlay="$emit('videoPlay', video)"
      @videoPause="$emit('videoPause', video)"
      @videoEnded="$emit('videoEnded', video)"
      @toggleOptions="$emit('toggleOptions', $event, video.id)"
      @goToChannel="$emit('goToChannel', video.channel_id)"
      @videoEnterViewport="$emit('videoEnterViewport', video)"
      @videoLeaveViewport="$emit('videoLeaveViewport', video)"
      @imageLoaded="onImageLoaded"
    />
  </div>
</template>

<script setup>
import {ref, onMounted, onUnmounted, watch, nextTick} from 'vue';
import VideoItem from './VideoItem.vue';

const props = defineProps({
  videos: Array,
  loading: Boolean,
  showAvatar: {
    type: Boolean,
    default: true
  },
  setVideoRef: Function,
});

const emit = defineEmits([
  'play',
  'videoPlay',
  'videoPause',
  'videoEnded',
  'toggleOptions',
  'goToChannel',
  'videoEnterViewport',
  'videoLeaveViewport',
]);

const waterfall = ref(null);
const loadedImages = ref(0);

const updateLayout = () => {
  if (!waterfall.value) return;

  const items = waterfall.value.children;
  const gap = 16; // 设置间隙
  const minColumnWidth = 240; // 设置最小列宽

  // 计算列数
  const containerWidth = waterfall.value.offsetWidth;
  const columnCount = Math.floor((containerWidth + gap) / (minColumnWidth + gap));
  const columnWidth = (containerWidth - (columnCount - 1) * gap) / columnCount;

  // 初始化列高度数组
  const columnHeights = new Array(columnCount).fill(0);

  // 遍历所有项目并放置
  Array.from(items).forEach((item) => {
    // 找出最短的列
    const minHeight = Math.min(...columnHeights);
    const column = columnHeights.indexOf(minHeight);

    // 设置项目的位置
    item.style.position = 'absolute';
    item.style.left = `${column * (columnWidth + gap)}px`;
    item.style.top = `${minHeight}px`;
    item.style.width = `${columnWidth}px`;

    // 更新列高度
    columnHeights[column] += item.offsetHeight + gap;
  });

  // 设置容器高度
  waterfall.value.style.height = `${Math.max(...columnHeights)}px`;
};

const onImageLoaded = () => {
  loadedImages.value++;
  if (loadedImages.value === props.videos.length) {
    updateLayout();
  }
};

onMounted(() => {
  window.addEventListener('resize', updateLayout);
});

onUnmounted(() => {
  window.removeEventListener('resize', updateLayout);
});

watch(() => props.videos, () => {
  loadedImages.value = 0;
  nextTick(() => {
    if (loadedImages.value === props.videos.length) {
      updateLayout();
    }
  });
}, { deep: true });
</script>

<style scoped>
.video-waterfall {
  position: relative;
  width: 100%;
}
</style>