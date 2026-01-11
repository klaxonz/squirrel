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
  background: var(--sp-overlay-strong);
  backdrop-filter: blur(12px);
  border: 1px solid var(--sp-border);
  box-shadow: var(--sp-shadow-lg);
}

.indicator-icon {
  @apply text-2xl;
  color: var(--sp-text);
  filter: drop-shadow(var(--sp-drop-shadow-md));
}

.indicator-text {
  @apply text-sm font-medium;
  color: var(--sp-text);
  font-family: var(--sp-font-family);
  text-shadow: var(--sp-text-shadow);
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
