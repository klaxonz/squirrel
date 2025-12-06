<template>
  <div 
    class="play-overlay" 
    v-if="!playing && !loading && canPlay"
    @click="$emit('play')"
  >
    <div class="play-button">
      <Icon icon="material-symbols:play-arrow" class="play-icon" />
    </div>
    
    <!-- YouTube风格的渐变背景 -->
    <div class="overlay-gradient"></div>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'

const props = defineProps({
  playing: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  canPlay: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['play'])
</script>

<style scoped>
.play-overlay {
  @apply absolute inset-0 z-20 cursor-pointer
    flex items-center justify-center;
  transition: opacity 0.3s ease;
}

.play-overlay:hover .play-button {
  transform: scale(1.06);
  background: #f1f1f1;
}

.play-overlay:hover .play-button .play-icon {
  color: #000000;
}

.play-button {
  @apply relative z-10 rounded-full
    flex items-center justify-center;
  width: 64px;
  height: 64px;
  background: #ffffff;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
  transition: transform 0.2s ease, background-color 0.2s ease, box-shadow 0.2s ease;
}

.play-icon {
  font-size: 30px;
  color: #212121;
  margin-left: 2px; /* 视觉居中调整 */
}

.overlay-gradient {
  @apply absolute inset-0;
  background: radial-gradient(
    circle at center,
    rgba(0, 0, 0, 0.3) 0%,
    rgba(0, 0, 0, 0.1) 40%,
    transparent 70%
  );
  pointer-events: none;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .play-button {
    width: 54px;
    height: 54px;
  }

  .play-icon {
    font-size: 26px;
  }
}
</style>
