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
  @apply p-2 rounded-full bg-transparent
    transition-all duration-200 flex items-center justify-center;
  min-width: 40px;
  min-height: 40px;
  color: var(--sp-text-strong);
}

.control-btn:hover {
  background: var(--sp-bg-hover);
  color: var(--sp-text);
  transform: scale(1.05);
}

.control-btn:active {
  transform: scale(0.95);
}

.control-btn:focus-visible {
  outline: 2px solid var(--sp-primary);
  outline-offset: 2px;
}

.playback-rate-text {
  @apply text-sm font-medium text-center;
  font-family: var(--sp-font-family);
  text-shadow: var(--sp-text-shadow);
  min-width: 24px;
}

.playback-rate-menu {
  @apply absolute bottom-full right-0 mb-3 w-24
    rounded-xl p-2
    border;
  background: var(--sp-menu-bg);
  backdrop-filter: blur(12px);
  border-color: var(--sp-border);
  box-shadow: var(--sp-shadow-lg);
}

.rate-option {
  @apply w-full text-center px-3 py-2 rounded-lg text-sm
    transition-all duration-200;
  color: var(--sp-text-secondary);
  font-family: var(--sp-font-family);
}

.rate-option:hover {
  color: var(--sp-text);
  background: var(--sp-bg-hover);
  transform: translateX(1px);
}

.rate-option.active {
  color: var(--sp-text);
  background: rgba(var(--sp-primary-rgb), 0.15);
  border-left: 3px solid var(--sp-primary);
}
</style>
