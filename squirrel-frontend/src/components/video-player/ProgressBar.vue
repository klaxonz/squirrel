<template>
  <div class="progress-container">
    <!-- YouTube风格的预览 -->
    <ProgressPreview
      :visible="hovering"
      :position="hoverPosition"
      :preview-time="previewTime"
    />

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
import ProgressPreview from './ProgressPreview.vue'
import ChapterMarkers from './ChapterMarkers.vue'

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

const handleChapterSeek = (time) => {
  emit('seek', time)
}

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
    rounded-full border-2 border-white
    opacity-0;
  width: 12px;
  height: 12px;
  background: var(--yt-red);
  box-shadow: var(--yt-shadow-light);
  transition: all var(--yt-transition-fast) ease;
}

.progress-handle {
  @apply absolute top-1/2 transform -translate-x-1/2 -translate-y-1/2
    rounded-full border-2 border-white
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
}
</style>
