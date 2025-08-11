<template>
  <div class="loading-spinner-container">
    <div class="yt-loading-spinner">
      <div class="yt-spinner">
        <svg class="yt-spinner__circle" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45"/>
        </svg>
      </div>
      
      <!-- 中央加载速度信息 -->
      <div class="loading-speed-info" v-if="networkSpeed">
        <div class="loading-speed-text">{{ networkSpeed }}</div>
      </div>
    </div>

    <!-- 左下角加载状态提示 -->
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
  }
})
</script>

<style scoped>
.loading-spinner-container {
  @apply absolute inset-0 z-30;
}

.yt-loading-spinner {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
    flex flex-col items-center justify-center;
}

.yt-spinner {
  @apply relative w-12 h-12;
}

.yt-spinner__circle {
  @apply w-full h-full;
  animation: media-spinner 1.4s linear infinite;
}

.yt-spinner__circle circle {
  @apply fill-none stroke-white stroke-2;
  stroke-dasharray: 80, 200;
  stroke-dashoffset: 0;
  stroke-linecap: round;
  animation: spinner-dash 1.4s ease-in-out infinite;
}

.loading-speed-info {
  @apply mt-4 text-center;
}

.loading-speed-text {
  @apply text-white text-sm font-medium px-3 py-1 rounded-full;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  font-family: 'Roboto', sans-serif;
}

.loading-status-indicator {
  @apply absolute bottom-6 left-6;
}

.loading-status-text {
  @apply text-white text-sm px-3 py-2 rounded-lg;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  font-family: 'Roboto', sans-serif;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
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
