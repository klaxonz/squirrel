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
  @apply flex items-center text-white text-sm font-medium
    px-2 py-1;
  font-family: 'Roboto', 'YouTube Noto', sans-serif;
  letter-spacing: 0.5px;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
  min-width: 80px;
}

.current-time {
  @apply text-white;
  font-weight: 500;
}

.time-separator {
  @apply text-white/70 mx-1;
}

.total-time {
  @apply text-white/90;
  font-weight: 400;
}
</style>
