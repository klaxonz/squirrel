<template>
  <div class="progress-container">
    <!-- 章节标记 -->
    <ChapterMarkers
      :chapters="chapters"
      :duration="duration"
      @seek-to-chapter="handleChapterSeek"
    />

    <!-- 进度条容器 -->
    <div
      class="progress-bar-container"
      @mouseenter="handleMouseEnter"
      @mousemove="handleMouseMove"
      @mouseleave="handleMouseLeave"
      @mousedown="handleMouseDown"
      @touchstart="handleTouchStart"
      @touchmove="handleTouchMove"
      @touchend="handleTouchEnd"
    >
      <div class="progress-bar">
        <!-- 缓冲进度 -->
        <div 
          class="progress-bar-loaded" 
          :style="{ width: bufferedProgress + '%' }"
        ></div>
        
        <!-- 播放进度 -->
        <div 
          class="progress-bar-filled" 
          :style="{ width: progress + '%' }"
        ></div>
        

      </div>
      
      <!-- 进度点 -->
      <div
        class="progress-dot"
        :style="{ left: progress + '%' }"
        v-show="isDragging"
      ></div>
      
      <!-- 进度手柄 -->
      <div
        class="progress-handle"
        :style="{ left: progress + '%' }"
        v-show="isDragging"
      ></div>

      <!-- 时间预览 -->
      <div
        v-if="showPreview && !isDragging"
        class="time-preview"
        :style="{ left: previewPosition + '%' }"
      >
        {{ formatTime(previewTime) }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ChapterMarkers from './ChapterMarkers.vue'
import { formatTime } from '../../utils/dateFormat'

const props = defineProps({
  progress: Number,
  bufferedProgress: Number,
  duration: Number,
  currentTime: Number,
  chapters: Array
})

const emit = defineEmits(['seek'])

const handleChapterSeek = (time) => {
  emit('seek', time)
}

const isDragging = ref(false)
const showPreview = ref(false)
const previewPosition = ref(0)
const previewTime = ref(0)

// 计算跳转时间
const calculateSeekTime = (clientX, rect) => {
  const percentage = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
  return percentage * props.duration
}

// 鼠标事件处理
const handleMouseEnter = () => {
  // 进入进度条区域时不需要特殊处理
}

const handleMouseMove = (event) => {
  if (isDragging.value) return

  const rect = event.currentTarget.getBoundingClientRect()
  const percentage = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width))

  previewPosition.value = percentage * 100
  previewTime.value = percentage * props.duration
  showPreview.value = true
}

const handleMouseLeave = () => {
  showPreview.value = false
}

const handleMouseDown = (event) => {
  isDragging.value = true
  const rect = event.currentTarget.getBoundingClientRect()
  const seekTime = calculateSeekTime(event.clientX, rect)

  emit('seek', seekTime)

  const handleMouseMove = (moveEvent) => {
    const newSeekTime = calculateSeekTime(moveEvent.clientX, rect)
    emit('seek', newSeekTime)
  }

  const handleMouseUp = () => {
    isDragging.value = false
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
  }

  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)

  event.preventDefault()
}

// 触摸事件处理
const handleTouchStart = (event) => {
  isDragging.value = true
  const touch = event.touches[0]
  const rect = event.currentTarget.getBoundingClientRect()
  const seekTime = calculateSeekTime(touch.clientX, rect)

  emit('seek', seekTime)
  event.preventDefault()
}

const handleTouchMove = (event) => {
  if (!isDragging.value) return

  const touch = event.touches[0]
  const rect = event.currentTarget.getBoundingClientRect()
  const seekTime = calculateSeekTime(touch.clientX, rect)

  emit('seek', seekTime)
  event.preventDefault()
}

const handleTouchEnd = () => {
  isDragging.value = false
}
</script>

<style scoped>
.progress-container {
  @apply relative mb-3;
  padding: 0 12px;
}





.progress-bar-container {
  @apply relative h-5 cursor-pointer flex items-center;
  padding: 8px 0;
}

.progress-bar {
  @apply relative w-full bg-white/30 rounded-full overflow-hidden
    transition-all duration-200;
  height: 3px;
}

.progress-bar-loaded {
  @apply absolute top-0 left-0 h-full transition-all duration-300;
  background: rgba(255, 255, 255, 0.4);
}

.progress-bar-filled {
  @apply absolute top-0 left-0 h-full;
  background: var(--yt-red);
  box-shadow: 0 0 8px var(--yt-red-glow);
  transition: all var(--yt-transition-fast) ease;
}

.progress-bar-hover {
  @apply absolute top-0 w-0.5 h-full bg-white/90;
  box-shadow: 0 0 4px rgba(255, 255, 255, 0.5);
}

.progress-dot {
  @apply absolute top-1/2 transform -translate-x-1/2 -translate-y-1/2
    rounded-full
    opacity-0;
  width: 12px;
  height: 12px;
  background: var(--yt-red);
  box-shadow: var(--yt-shadow-light);
  transition: all var(--yt-transition-fast) ease;
}

.progress-handle {
  @apply absolute top-1/2 transform -translate-x-1/2 -translate-y-1/2
    rounded-full
    opacity-0;
  width: 14px;
  height: 14px;
  background: var(--yt-red);
  box-shadow: var(--yt-shadow-medium);
  transition: all var(--yt-transition-fast) ease;
}

.progress-bar-container:hover .progress-handle {
  @apply opacity-100;
}

.progress-bar-container:hover .progress-dot {
  @apply opacity-100;
}

.progress-bar-container:hover .progress-bar {
  height: 5px;
}

.time-preview {
  @apply absolute bottom-full mb-2 transform -translate-x-1/2
    text-white text-xs font-medium px-2 py-1 rounded-md
    pointer-events-none z-30;
  background: rgba(0, 0, 0, 0.9);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  font-family: 'Roboto', sans-serif;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
  white-space: nowrap;
  animation: fadeIn 0.2s ease-out;
}

.time-preview::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 4px solid transparent;
  border-top-color: rgba(0, 0, 0, 0.9);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateX(-50%) translateY(4px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

/* 触摸设备优化 */
@media (hover: none), (pointer: coarse) {
  .progress-bar {
    height: 4px;
  }

  .progress-bar-container {
    @apply h-8;
    padding: 12px 0;
  }

  .progress-dot {
    @apply opacity-100;
    width: 16px;
    height: 16px;
  }

  .progress-handle {
    width: 18px;
    height: 18px;
  }

  .time-preview {
    display: none;
  }
}

/* 全屏状态下的样式修复 */
:fullscreen .progress-container,
:-webkit-full-screen .progress-container,
:-moz-full-screen .progress-container {
  z-index: 2147483647; /* 最高 z-index 值 */
  position: relative;
}

:fullscreen .time-preview,
:-webkit-full-screen .time-preview,
:-moz-full-screen .time-preview {
  z-index: 2147483648; /* 比进度条更高 */
}
</style>
