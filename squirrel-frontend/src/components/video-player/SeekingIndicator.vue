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
    rounded-xl p-6
    border border-white/10 shadow-2xl z-30;
  background: rgba(40, 40, 40, 0.95);
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
  animation: seekingIndicatorShow 0.3s ease-out;
}

.seeking-content {
  @apply flex flex-col items-center;
}

.seeking-icon-container {
  @apply flex flex-col items-center gap-3;
}

.seeking-icon {
  @apply text-white text-5xl;
  filter: drop-shadow(0 2px 8px rgba(0,0,0,0.4));
}

.seeking-seconds {
  @apply text-white text-base font-medium;
  font-family: 'Roboto', sans-serif;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
}

/* 方向指示动画 */
.seeking-indicator[data-direction="forward"] .seeking-icon {
  animation: seek-forward 0.4s ease-out;
}

.seeking-indicator[data-direction="backward"] .seeking-icon {
  animation: seek-backward 0.4s ease-out;
}

@keyframes seekingIndicatorShow {
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

@keyframes seek-forward {
  0% {
    transform: translateX(-15px);
    opacity: 0.6;
  }
  50% {
    transform: translateX(5px);
    opacity: 1;
  }
  100% {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes seek-backward {
  0% {
    transform: translateX(15px);
    opacity: 0.6;
  }
  50% {
    transform: translateX(-5px);
    opacity: 1;
  }
  100% {
    transform: translateX(0);
    opacity: 1;
  }
}
</style>
