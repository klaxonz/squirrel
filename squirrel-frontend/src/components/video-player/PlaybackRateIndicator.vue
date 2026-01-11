<template>
  <div class="playback-rate-indicator" v-if="showIndicator">
    <div class="rate-indicator-content">
      <Icon icon="material-symbols:speed" class="rate-icon" />
      <span class="rate-text">{{ playbackRate }}x</span>
    </div>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'

const props = defineProps({
  showIndicator: {
    type: Boolean,
    default: false
  },
  playbackRate: {
    type: Number,
    default: 1
  }
})
</script>

<style scoped>
.playback-rate-indicator {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
    pointer-events-none z-30;
  animation: rateIndicatorShow 0.3s ease-out;
}

.rate-indicator-content {
  @apply flex items-center gap-3 px-4 py-3 rounded-xl;
  background: var(--sp-overlay-strong);
  backdrop-filter: blur(12px);
  border: 1px solid var(--sp-border);
  box-shadow: var(--sp-shadow-lg);
}

.rate-icon {
  @apply text-xl;
  color: var(--sp-text);
  filter: drop-shadow(var(--sp-drop-shadow-sm));
}

.rate-text {
  @apply text-sm font-medium;
  color: var(--sp-text);
  font-family: var(--sp-font-family);
  text-shadow: var(--sp-text-shadow);
  min-width: 32px;
  text-align: center;
}

@keyframes rateIndicatorShow {
  0% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.8);
  }
  50% {
    transform: translate(-50%, -50%) scale(1.05);
  }
  100% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}
</style>
