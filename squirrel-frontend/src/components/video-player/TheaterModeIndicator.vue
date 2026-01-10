<template>
  <div class="theater-mode-indicator" v-if="showIndicator">
    <div class="indicator-content">
      <Icon icon="material-symbols:fit-screen" class="indicator-icon" />
      <span class="indicator-text">{{ theaterMode ? '退出剧场模式' : '剧场模式' }}</span>
    </div>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'

const props = defineProps({
  theaterMode: {
    type: Boolean,
    default: false
  },
  showIndicator: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.theater-mode-indicator {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
    pointer-events-none z-30;
  animation: theaterIndicatorShow 0.6s ease-out;
}

.indicator-content {
  @apply flex items-center gap-3 px-4 py-3 rounded-xl;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
}

.indicator-icon {
  @apply text-text-primary text-2xl;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
}

.indicator-text {
  @apply text-text-primary text-sm font-medium;
  font-family: 'Roboto', sans-serif;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
}

@keyframes theaterIndicatorShow {
  0% {
    transform: translate(-50%, -50%) scale(0.8);
    opacity: 0;
  }
  50% {
    transform: translate(-50%, -50%) scale(1.05);
    opacity: 1;
  }
  100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 1;
  }
}
</style>
