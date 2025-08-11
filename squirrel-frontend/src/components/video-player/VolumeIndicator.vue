<template>
  <div class="volume-adjust-indicator">
    <div class="volume-control-container">
      <Icon :icon="volumeIcon" class="volume-icon" />
      <div class="volume-slider">
        <div class="volume-slider-track"></div>
        <div class="volume-slider-fill" :style="{ height: volume + '%' }"></div>
      </div>
      <div class="volume-value">{{ Math.round(volume) }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Icon } from '@iconify/vue'

const props = defineProps({
  volume: {
    type: Number,
    default: 0
  },
  muted: {
    type: Boolean,
    default: false
  }
})

const volumeIcon = computed(() => {
  if (props.muted || props.volume === 0)
    return 'material-symbols:volume-off'
  if (props.volume < 50)
    return 'material-symbols:volume-down'
  return 'material-symbols:volume-up'
})
</script>

<style scoped>
.volume-adjust-indicator {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
    rounded-xl p-4
    border border-white/10 shadow-2xl z-30;
  background: rgba(40, 40, 40, 0.95);
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
  animation: volumeIndicatorShow 0.3s ease-out;
}

.volume-control-container {
  @apply flex flex-col items-center gap-3;
}

.volume-icon {
  @apply text-white text-xl;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3));
}

.volume-slider {
  @apply relative rounded-full overflow-hidden;
  width: 4px;
  height: 80px;
  background: rgba(255, 255, 255, 0.3);
}

.volume-slider-track {
  @apply absolute inset-0 rounded-full;
  background: rgba(255, 255, 255, 0.2);
}

.volume-slider-fill {
  @apply absolute bottom-0 left-0 w-full rounded-full
    transition-all duration-200;
  background: #ffffff;
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.3);
}

.volume-value {
  @apply text-white text-sm font-medium text-center;
  font-family: 'Roboto', sans-serif;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
  min-width: 32px;
}

@keyframes volumeIndicatorShow {
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
