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
  background: var(--sp-overlay-strong);
  backdrop-filter: blur(12px);
  border: 1px solid var(--sp-border);
  box-shadow: var(--sp-shadow-lg);
}

.volume-icon {
  @apply text-xl;
  color: var(--sp-text);
  filter: drop-shadow(var(--sp-drop-shadow-sm));
}

.volume-bars {
  @apply flex items-end gap-1;
}

.volume-bar {
  @apply rounded-sm transition-all duration-200;
  width: 3px;
  background: var(--sp-text-disabled);
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
  background: var(--sp-text);
  box-shadow: var(--sp-shadow-sm);
}

.volume-bar.muted {
  background: rgba(var(--sp-primary-rgb), 0.6);
}

.volume-text {
  @apply text-sm font-medium;
  color: var(--sp-text);
  font-family: var(--sp-font-family);
  text-shadow: var(--sp-text-shadow);
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
