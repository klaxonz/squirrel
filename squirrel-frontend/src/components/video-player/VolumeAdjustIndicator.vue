<template>
  <div class="volume-adjust-indicator" v-if="showIndicator">
    <div class="volume-indicator-content">
      <Icon :icon="volumeIcon" class="volume-icon" />
      <div class="volume-bars">
        <div 
          v-for="i in 10" 
          :key="i"
          class="volume-bar"
          :class="{ 
            'active': i <= Math.ceil(volume / 10),
            'muted': muted 
          }"
        ></div>
      </div>
      <span class="volume-text">{{ muted ? '静音' : Math.round(volume) }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Icon } from '@iconify/vue'

const props = defineProps({
  showIndicator: {
    type: Boolean,
    default: false
  },
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
    pointer-events-none z-30;
  animation: volumeAdjustShow 0.3s ease-out;
}

.volume-indicator-content {
  @apply flex items-center gap-3 px-4 py-3 rounded-xl;
  background: rgba(40, 40, 40, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
}

.volume-icon {
  @apply text-white text-xl;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3));
}

.volume-bars {
  @apply flex items-end gap-1;
}

.volume-bar {
  @apply rounded-sm transition-all duration-200;
  width: 3px;
  background: rgba(255, 255, 255, 0.3);
}

.volume-bar:nth-child(1) { height: 4px; }
.volume-bar:nth-child(2) { height: 6px; }
.volume-bar:nth-child(3) { height: 8px; }
.volume-bar:nth-child(4) { height: 10px; }
.volume-bar:nth-child(5) { height: 12px; }
.volume-bar:nth-child(6) { height: 14px; }
.volume-bar:nth-child(7) { height: 16px; }
.volume-bar:nth-child(8) { height: 18px; }
.volume-bar:nth-child(9) { height: 20px; }
.volume-bar:nth-child(10) { height: 22px; }

.volume-bar.active {
  background: #ffffff;
  box-shadow: 0 0 4px rgba(255, 255, 255, 0.3);
}

.volume-bar.muted {
  background: rgba(255, 0, 0, 0.6);
}

.volume-text {
  @apply text-white text-sm font-medium;
  font-family: 'Roboto', sans-serif;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
  min-width: 32px;
  text-align: center;
}

@keyframes volumeAdjustShow {
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
