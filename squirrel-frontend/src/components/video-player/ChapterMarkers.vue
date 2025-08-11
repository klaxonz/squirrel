<template>
  <div class="chapter-markers" v-if="chapters && chapters.length > 0">
    <div
      v-for="chapter in chapters"
      :key="chapter.id"
      class="chapter-marker"
      :style="{ left: (chapter.time / duration) * 100 + '%' }"
      :title="chapter.title"
      @click="$emit('seek-to-chapter', chapter.time)"
    >
      <div class="marker-dot"></div>
      <div class="marker-tooltip">
        <span class="tooltip-title">{{ chapter.title }}</span>
        <span class="tooltip-time">{{ formatTime(chapter.time) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatTime } from '../../utils/dateFormat'

const props = defineProps({
  chapters: {
    type: Array,
    default: () => []
  },
  duration: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['seek-to-chapter'])
</script>

<style scoped>
.chapter-markers {
  @apply absolute top-0 left-0 right-0 h-full pointer-events-none;
}

.chapter-marker {
  @apply absolute top-1/2 transform -translate-x-1/2 -translate-y-1/2
    pointer-events-auto cursor-pointer;
}

.marker-dot {
  @apply rounded-full transition-all duration-200;
  width: 4px;
  height: 4px;
  background: var(--yt-text-secondary);
  box-shadow: 0 0 4px rgba(0, 0, 0, 0.3);
}

.chapter-marker:hover .marker-dot {
  width: 6px;
  height: 6px;
  background: var(--yt-text-primary);
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.3);
}

.marker-tooltip {
  @apply absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2
    px-3 py-2 rounded-lg opacity-0 pointer-events-none
    transition-all duration-200 flex flex-col items-center;
  background: var(--yt-bg-overlay);
  backdrop-filter: blur(8px);
  border: 1px solid var(--yt-control-border);
  box-shadow: var(--yt-shadow-medium);
  min-width: 120px;
}

.chapter-marker:hover .marker-tooltip {
  @apply opacity-100;
  transform: translateX(-50%) translateY(-4px);
}

.tooltip-title {
  @apply text-white text-xs font-medium mb-1;
  font-family: var(--yt-font-family);
  text-align: center;
  line-height: 1.2;
}

.tooltip-time {
  @apply text-white/70 text-xs;
  font-family: var(--yt-font-family);
}

.marker-tooltip::after {
  content: '';
  @apply absolute top-full left-1/2 transform -translate-x-1/2;
  border: 4px solid transparent;
  border-top-color: var(--yt-bg-overlay);
}
</style>
