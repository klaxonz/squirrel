<template>
  <div class="buffering-indicator" v-if="isBuffering">
    <div class="buffering-spinner">
      <div class="spinner-ring"></div>
      <div class="spinner-ring"></div>
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
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
    pointer-events-none z-30;
}

.buffering-spinner {
  @apply relative;
  width: 40px;
  height: 40px;
}

.spinner-ring {
  @apply absolute border-2 border-transparent rounded-full;
  width: 40px;
  height: 40px;
  border-top-color: rgba(255, 255, 255, 0.8);
  animation: bufferingRotate 1.2s linear infinite;
}

.spinner-ring:nth-child(1) {
  animation-delay: 0s;
}

.spinner-ring:nth-child(2) {
  animation-delay: 0.4s;
  width: 32px;
  height: 32px;
  top: 4px;
  left: 4px;
  border-top-color: rgba(255, 255, 255, 0.6);
}

.spinner-ring:nth-child(3) {
  animation-delay: 0.8s;
  width: 24px;
  height: 24px;
  top: 8px;
  left: 8px;
  border-top-color: rgba(255, 255, 255, 0.4);
}

.buffering-speed {
  @apply mt-3 text-white text-sm text-center;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
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
