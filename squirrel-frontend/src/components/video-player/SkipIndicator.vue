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
  background: var(--sp-overlay-strong);
  backdrop-filter: blur(12px);
  border: 1px solid var(--sp-border);
  box-shadow: var(--sp-shadow-lg);
}

.skip-icon {
  @apply text-3xl;
  color: var(--sp-text);
  filter: drop-shadow(var(--sp-drop-shadow-md));
}

.skip-text {
  @apply text-sm font-medium;
  color: var(--sp-text);
  font-family: var(--sp-font-family);
  text-shadow: var(--sp-text-shadow);
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
