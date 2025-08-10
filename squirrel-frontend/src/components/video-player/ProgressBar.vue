<template>
  <div class="progress-container">
    <!-- 预览时间提示 -->
    <div 
      class="preview-time-tooltip"
      :style="{ left: hoverPosition + '%' }"
      v-show="hovering"
    >
      <div class="tooltip-content">
        {{ formatTime(previewTime) }}
      </div>
      <div class="tooltip-arrow"></div>
    </div>

    <!-- 章节标记 -->
    <div class="chapter-markers" v-if="chapters && chapters.length > 0">
      <div
        v-for="chapter in chapters"
        :key="chapter.id"
        class="chapter-marker"
        :style="{ left: (chapter.time / duration) * 100 + '%' }"
        :title="chapter.title"
      ></div>
    </div>

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
        
        <!-- 悬停预览线 -->
        <div 
          class="progress-bar-hover"
          :style="{ left: hoverPosition + '%' }"
          v-show="hovering"
        ></div>
      </div>
      
      <!-- 进度点 -->
      <div 
        class="progress-dot"
        :style="{ left: progress + '%' }"
        v-show="hovering || isDragging"
      ></div>
      
      <!-- 进度手柄 -->
      <div 
        class="progress-handle"
        :style="{ left: progress + '%' }"
        v-show="hovering"
      ></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { formatTime } from '../../utils/dateFormat'
import { debounce } from 'lodash-es'

const props = defineProps({
  progress: Number,
  bufferedProgress: Number,
  duration: Number,
  currentTime: Number,
  chapters: Array,
  hovering: Boolean,
  hoverPosition: Number,
  previewTime: Number
})

const emit = defineEmits(['seek', 'hover-start', 'hover-end', 'hover-move'])

const isDragging = ref(false)
const progressContainer = ref(null)
const isHovering = ref(false)

// 计算预览时间
const calculatePreviewTime = (clientX, rect) => {
  const percentage = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
  return percentage * props.duration
}

// 计算位置百分比
const calculatePosition = (clientX, rect) => {
  return Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100))
}

// 鼠标事件处理
const handleMouseEnter = () => {
  isHovering.value = true
  emit('hover-start')
}

const handleMouseMove = debounce((event) => {
  if (!isHovering.value) {
    isHovering.value = true
    emit('hover-start')
  }

  const rect = event.currentTarget.getBoundingClientRect()
  const previewTime = calculatePreviewTime(event.clientX, rect)
  const position = calculatePosition(event.clientX, rect)

  emit('hover-move', {
    previewTime,
    position,
    hovering: true
  })
}, 16) // 约60fps

const handleMouseLeave = () => {
  if (!isDragging.value) {
    isHovering.value = false
    emit('hover-end')
  }
}

const handleMouseDown = (event) => {
  isDragging.value = true
  const rect = event.currentTarget.getBoundingClientRect()
  const seekTime = calculatePreviewTime(event.clientX, rect)
  
  emit('seek', seekTime)
  
  const handleMouseMove = (moveEvent) => {
    const newSeekTime = calculatePreviewTime(moveEvent.clientX, rect)
    emit('seek', newSeekTime)
  }
  
  const handleMouseUp = () => {
    isDragging.value = false
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
    emit('hover-end')
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
  const seekTime = calculatePreviewTime(touch.clientX, rect)
  
  emit('seek', seekTime)
  event.preventDefault()
}

const handleTouchMove = (event) => {
  if (!isDragging.value) return
  
  const touch = event.touches[0]
  const rect = event.currentTarget.getBoundingClientRect()
  const seekTime = calculatePreviewTime(touch.clientX, rect)
  
  emit('seek', seekTime)
  event.preventDefault()
}

const handleTouchEnd = () => {
  isDragging.value = false
  emit('hover-end')
}
</script>

<style scoped>
.progress-container {
  @apply relative mb-2;
}

.preview-time-tooltip {
  @apply absolute bottom-full mb-2 transform -translate-x-1/2
    bg-black/80 text-white text-xs px-2 py-1 rounded
    pointer-events-none z-10;
}

.tooltip-content {
  @apply whitespace-nowrap;
}

.tooltip-arrow {
  @apply absolute top-full left-1/2 transform -translate-x-1/2
    w-0 h-0 border-l-4 border-r-4 border-t-4
    border-l-transparent border-r-transparent border-t-black/80;
}

.chapter-markers {
  @apply absolute top-0 left-0 right-0 h-full pointer-events-none;
}

.chapter-marker {
  @apply absolute top-0 w-0.5 h-full bg-white/60;
}

.progress-bar-container {
  @apply relative h-3 cursor-pointer flex items-center;
}

.progress-bar {
  @apply relative w-full h-1 bg-white/20 rounded-full overflow-hidden;
}

.progress-bar-loaded {
  @apply absolute top-0 left-0 h-full bg-white/40 transition-all duration-200;
}

.progress-bar-filled {
  @apply absolute top-0 left-0 h-full bg-red-500 transition-all duration-200;
}

.progress-bar-hover {
  @apply absolute top-0 w-0.5 h-full bg-white/80;
}

.progress-dot {
  @apply absolute top-1/2 transform -translate-x-1/2 -translate-y-1/2
    w-3 h-3 bg-red-500 rounded-full border-2 border-white
    transition-all duration-200;
}

.progress-handle {
  @apply absolute top-1/2 transform -translate-x-1/2 -translate-y-1/2
    w-4 h-4 bg-red-500 rounded-full border-2 border-white
    opacity-0 transition-all duration-200;
}

.progress-bar-container:hover .progress-handle {
  @apply opacity-100;
}

.progress-bar-container:hover .progress-bar {
  @apply h-1.5;
}

/* 触摸设备优化 */
@media (hover: none), (pointer: coarse) {
  .progress-bar {
    @apply h-2;
  }
  
  .progress-bar-container {
    @apply h-6;
  }
  
  .progress-dot {
    @apply w-4 h-4;
  }
}
</style>
