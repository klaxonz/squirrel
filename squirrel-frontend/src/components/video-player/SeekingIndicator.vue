<template>
  <div 
    class="seeking-indicator" 
    :data-direction="seekingState.direction"
  >
    <div class="seeking-content">
      <div class="seeking-icon-container">
        <Icon 
          :icon="seekingState.direction === 'forward' 
            ? 'material-symbols:fast-forward-rounded' 
            : 'material-symbols:fast-rewind-rounded'" 
          class="seeking-icon" 
        />
        <div class="seeking-seconds">
          {{ Math.round(Math.abs(seekingState.seekTime - seekingState.currentTime)) }}秒
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'

const props = defineProps({
  seekingState: Object
})
</script>

<style scoped>
.seeking-indicator {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
    bg-black/70 backdrop-blur-sm rounded-lg p-6
    border border-white/10 shadow-xl z-30;
}

.seeking-content {
  @apply flex flex-col items-center;
}

.seeking-icon-container {
  @apply flex flex-col items-center gap-2;
}

.seeking-icon {
  @apply text-white text-4xl;
}

.seeking-seconds {
  @apply text-white text-lg font-medium;
}

/* 方向指示动画 */
.seeking-indicator[data-direction="forward"] .seeking-icon {
  animation: seek-forward 0.3s ease-out;
}

.seeking-indicator[data-direction="backward"] .seeking-icon {
  animation: seek-backward 0.3s ease-out;
}

@keyframes seek-forward {
  0% {
    transform: translateX(-10px);
    opacity: 0.5;
  }
  100% {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes seek-backward {
  0% {
    transform: translateX(10px);
    opacity: 0.5;
  }
  100% {
    transform: translateX(0);
    opacity: 1;
  }
}
</style>
