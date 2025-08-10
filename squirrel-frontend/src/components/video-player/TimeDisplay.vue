<template>
  <div class="time-display">
    <span class="current-time">{{ formatTime(currentTime) }}</span>
    <span class="time-separator">/</span>
    <span class="total-time">{{ formatTime(duration) }}</span>
  </div>
</template>

<script setup>
import { formatTime } from '../../utils/dateFormat'

const props = defineProps({
  currentTime: {
    type: Number,
    default: 0
  },
  duration: {
    type: Number,
    default: 0
  }
})
</script>

<style scoped>
.time-display {
  @apply flex items-center gap-1 text-white text-sm font-mono
    bg-black/20 px-2 py-1 rounded;
}

.current-time {
  @apply text-white;
}

.time-separator {
  @apply text-white/60;
}

.total-time {
  @apply text-white/80;
}
</style>
