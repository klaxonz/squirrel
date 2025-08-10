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
  @apply p-2 rounded-lg bg-black/20 hover:bg-black/40 
    transition-colors duration-200 text-white
    focus:outline-none focus:ring-2 focus:ring-white/50;
}

.playback-rate-text {
  @apply text-sm font-medium min-w-8 text-center;
}

.playback-rate-menu {
  @apply absolute bottom-full right-0 mb-2 w-20
    bg-black/90 backdrop-blur-sm rounded-lg p-2
    border border-white/10 shadow-xl;
}

.rate-option {
  @apply w-full text-center px-2 py-1 rounded text-sm
    text-white/80 hover:text-white hover:bg-white/10
    transition-colors duration-200;
}

.rate-option.active {
  @apply text-white bg-white/20;
}
</style>
