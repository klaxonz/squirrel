<template>
  <div class="volume-adjust-indicator">
    <div class="volume-control-container">
      <div class="volume-slider">
        <div class="volume-slider-fill" :style="{ height: volume + '%' }"></div>
        <div class="volume-slider-thumb"></div>
      </div>
      <div class="volume-value">{{ Math.round(volume) }}</div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  volume: {
    type: Number,
    default: 0
  }
})
</script>

<style scoped>
.volume-adjust-indicator {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
    bg-black/70 backdrop-blur-sm rounded-lg p-4
    border border-white/10 shadow-xl z-30;
}

.volume-control-container {
  @apply flex items-center gap-3;
}

.volume-slider {
  @apply relative w-2 h-20 bg-white/20 rounded-full overflow-hidden;
}

.volume-slider-fill {
  @apply absolute bottom-0 left-0 w-full bg-white rounded-full
    transition-all duration-200;
}

.volume-slider-thumb {
  @apply absolute w-3 h-3 bg-white rounded-full border-2 border-gray-800
    transform -translate-x-0.5 transition-all duration-200;
  bottom: calc(var(--volume-percentage, 0%) - 6px);
}

.volume-value {
  @apply text-white text-lg font-medium min-w-8 text-center;
}

/* 动画效果 */
.volume-adjust-indicator {
  animation: volume-appear 0.2s ease-out;
}

@keyframes volume-appear {
  0% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.8);
  }
  100% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}
</style>
