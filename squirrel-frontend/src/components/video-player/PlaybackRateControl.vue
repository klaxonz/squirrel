<template>
  <div class="playback-rate-control">
    <button 
      @click="$emit('toggle-menu')" 
      class="control-btn" 
      aria-label="播放速度"
    >
      <span class="playback-rate-text">{{ currentRate }}x</span>
    </button>

    <!-- 播放速度菜单 -->
    <div v-if="showMenu" class="playback-rate-menu">
      <button
        v-for="rate in rates"
        :key="rate"
        @click="$emit('set-rate', rate)"
        class="rate-option"
        :class="{ active: currentRate === rate }"
      >
        {{ rate }}x
      </button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  currentRate: Number,
  rates: Array,
  showMenu: Boolean
})

const emit = defineEmits(['toggle-menu', 'set-rate'])
</script>

<style scoped>
.playback-rate-control {
  @apply relative;
}

.control-btn {
  @apply p-2 rounded-full bg-transparent hover:bg-white/10
    transition-all duration-200 text-white
    focus:outline-none focus:ring-2 focus:ring-white/30
    flex items-center justify-center;
  min-width: 40px;
  min-height: 40px;
}

.control-btn:hover {
  transform: scale(1.05);
}

.control-btn:active {
  transform: scale(0.95);
}

.playback-rate-text {
  @apply text-sm font-medium text-center;
  font-family: 'Roboto', sans-serif;
  text-shadow: 0 1px 2px rgba(0,0,0,0.3);
  min-width: 24px;
}

.playback-rate-menu {
  @apply absolute bottom-full right-0 mb-3 w-24
    rounded-xl p-2
    border border-white/10 shadow-2xl;
  background: rgba(40, 40, 40, 0.95);
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
}

.rate-option {
  @apply w-full text-center px-3 py-2 rounded-lg text-sm
    text-white/80 hover:text-white hover:bg-white/10
    transition-all duration-200;
  font-family: 'Roboto', sans-serif;
}

.rate-option:hover {
  transform: translateX(1px);
}

.rate-option.active {
  @apply text-white;
  background: rgba(255, 0, 0, 0.15);
  border-left: 3px solid #ff0000;
}
</style>
