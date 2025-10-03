<template>
  <div class="buffering-indicator" v-if="isBuffering">
    <!-- 单个优化的加载圆圈 -->
    <div class="buffering-spinner">
      <div class="spinner-ring"></div>
    </div>
    <div v-if="networkSpeed" class="buffering-speed">{{ networkSpeed }}</div>
  </div>
</template>

<script setup>
const props = defineProps({
  isBuffering: {
    type: Boolean,
    default: false
  },
  networkSpeed: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.buffering-indicator {
  @apply absolute top-1/2 left-1/2
    pointer-events-none z-30
    flex flex-col items-center;
  transform: translate(-50%, -50%);
}

.buffering-spinner {
  @apply relative;
  width: 40px;
  height: 40px;
}

.spinner-ring {
  @apply absolute inset-0 rounded-full;
  border: 3px solid transparent;
  border-top-color: rgba(255, 255, 255, 0.9);
  border-right-color: rgba(255, 255, 255, 0.5);
  animation: bufferingRotate 0.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  will-change: transform;
  transform: translateZ(0);
  backface-visibility: hidden;
}

.buffering-speed {
  @apply mt-3 text-white text-sm text-center whitespace-nowrap;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

@keyframes bufferingRotate {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
</style>
