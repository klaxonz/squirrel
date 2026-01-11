<template>
  <div 
    class="progress-preview" 
    v-if="visible"
    :style="{ left: position + '%' }"
  >
    <!-- 预览时间 -->
    <div class="preview-time">
      {{ formatTime(previewTime) }}
    </div>
    
    <!-- 预览缩略图占位符 -->
    <div class="preview-thumbnail">
      <Icon icon="material-symbols:movie" class="thumbnail-icon" />
    </div>
    
    <!-- 箭头指示器 -->
    <div class="preview-arrow"></div>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'
import { formatTime } from '../../utils/dateFormat'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  position: {
    type: Number,
    default: 0
  },
  previewTime: {
    type: Number,
    default: 0
  }
})
</script>

<style scoped>
.progress-preview {
  @apply absolute bottom-full mb-2 transform -translate-x-1/2
    pointer-events-none z-20;
  animation: previewShow 0.2s ease-out;
}

.preview-time {
  @apply text-xs font-medium px-2 py-1 rounded-md mb-2
    text-center;
  background: var(--sp-tooltip-bg);
  backdrop-filter: blur(4px);
  border: 1px solid var(--sp-border);
  color: var(--sp-text);
  font-family: var(--sp-font-family);
  text-shadow: var(--sp-text-shadow);
}

.preview-thumbnail {
  @apply rounded-lg overflow-hidden
    flex items-center justify-center;
  width: 160px;
  height: 90px;
  background: var(--sp-bg-elevated);
  border: 1px solid var(--sp-border);
  box-shadow: var(--sp-shadow-md);
}

.thumbnail-icon {
  @apply text-2xl;
  color: var(--sp-text-tertiary);
}

.preview-arrow {
  @apply absolute top-full left-1/2 transform -translate-x-1/2
    w-0 h-0 border-l-4 border-r-4 border-t-4
    border-l-transparent border-r-transparent;
  border-top-color: var(--sp-tooltip-bg);
}

@keyframes previewShow {
  0% {
    opacity: 0;
    transform: translateX(-50%) translateY(-8px) scale(0.95);
  }
  100% {
    opacity: 1;
    transform: translateX(-50%) translateY(0) scale(1);
  }
}

/* 移动端优化 */
@media (max-width: 768px) {
  .preview-thumbnail {
    width: 120px;
    height: 68px;
  }
}
</style>
