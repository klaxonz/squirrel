<template>
  <div class="loading-spinner-container" :style="{ pointerEvents: statusOnly ? 'none' : undefined }">
    <div class="loading-spinner" v-if="!statusOnly">
      <!-- 使用纯 CSS 实现的加载圆圈 -->
      <div class="spinner-circle">
        <div class="spinner-arc"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  loadingText: {
    type: String,
    default: '加载中...'
  },
  networkSpeed: {
    type: String,
    default: ''
  },
  statusOnly: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.loading-spinner-container {
  @apply absolute inset-0 z-30;
  pointer-events: none;
}

.loading-spinner {
  @apply absolute top-1/2 left-1/2
    flex flex-col items-center justify-center;
  transform: translate(-50%, -50%);
}

.spinner-circle {
  @apply relative;
  width: 48px;
  height: 48px;
}

.spinner-arc {
  @apply absolute inset-0 rounded-full;
  border: 3px solid transparent;
  border-top-color: rgba(255, 255, 255, 0.9);
  border-right-color: rgba(255, 255, 255, 0.6);
  animation: spinner-rotate 0.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  will-change: transform;
}

@keyframes spinner-rotate {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

/* GPU 加速优化 */
.spinner-arc {
  transform: translateZ(0);
  backface-visibility: hidden;
}
</style>
