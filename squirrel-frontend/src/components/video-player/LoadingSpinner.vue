<template>
  <div class="loading-spinner-container" :style="{ pointerEvents: statusOnly ? 'none' : undefined }">
    <div class="loading-spinner" v-if="!statusOnly">
      <div class="spinner">
        <svg class="spinner__circle" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45"/>
        </svg>
      </div>
    </div>

    <!-- 左下角加载状态提示（共用） -->
    <div class="loading-status-indicator">
      <div class="loading-status-text">{{ loadingText }}</div>
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
}

.loading-spinner {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
    flex flex-col items-center justify-center;
}

.spinner {
  @apply relative w-12 h-12;
}

.spinner__circle {
  @apply w-full h-full;
  animation: media-spinner 1.4s linear infinite;
}

.spinner__circle circle {
  @apply fill-none stroke-white stroke-2;
  stroke-dasharray: 80, 200;
  stroke-dashoffset: 0;
  stroke-linecap: round;
  animation: spinner-dash 1.4s ease-in-out infinite;
}

.loading-status-indicator {
  @apply absolute left-6;
  bottom: 72px;
  pointer-events: none;
}

.loading-status-text {
  @apply text-sm;
  text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}

@keyframes media-spinner {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

@keyframes spinner-dash {
  0% {
    stroke-dasharray: 1, 200;
    stroke-dashoffset: 0;
  }
  50% {
    stroke-dasharray: 100, 200;
    stroke-dashoffset: -15;
  }
  100% {
    stroke-dasharray: 100, 200;
    stroke-dashoffset: -125;
  }
}
</style>
