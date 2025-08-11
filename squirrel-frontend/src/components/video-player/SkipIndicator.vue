<template>
  <div class="skip-indicator" v-if="showIndicator">
    <div class="skip-content">
      <Icon :icon="skipIcon" class="skip-icon" />
      <span class="skip-text">{{ skipText }}</span>
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
  direction: {
    type: String, // 'forward' or 'backward'
    default: 'forward'
  },
  seconds: {
    type: Number,
    default: 10
  }
})

const skipIcon = computed(() => {
  return props.direction === 'forward' 
    ? 'material-symbols:forward-10' 
    : 'material-symbols:replay-10'
})

const skipText = computed(() => {
  return props.direction === 'forward' 
    ? `+${props.seconds}秒` 
    : `-${props.seconds}秒`
})
</script>

<style scoped>
.skip-indicator {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
    pointer-events-none z-30;
  animation: skipIndicatorShow 0.6s ease-out;
}

.skip-content {
  @apply flex flex-col items-center gap-2 px-4 py-3 rounded-xl;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
}

.skip-icon {
  @apply text-white text-3xl;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
}

.skip-text {
  @apply text-white text-sm font-medium;
  font-family: 'Roboto', sans-serif;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
}

@keyframes skipIndicatorShow {
  0% {
    transform: translate(-50%, -50%) scale(0.8);
    opacity: 0;
  }
  50% {
    transform: translate(-50%, -50%) scale(1.1);
    opacity: 1;
  }
  100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 1;
  }
}
</style>
