<template>
  <div class="volume-control group">
    <button 
      @click="$emit('toggle-mute')" 
      class="control-btn" 
      :aria-label="muted ? '取消静音' : '静音'"
    >
      <Icon :icon="volumeIcon" class="control-icon" />
    </button>

    <div class="volume-slider-container">
      <div class="volume-slider-wrapper">
        <div class="volume-track-bg"></div>
        <div
          class="volume-range-fill"
          :style="{ width: `${muted ? 0 : Math.min(volume, 100)}%` }"
        ></div>
        <input
          type="range"
          min="0"
          max="100"
          :value="volume"
          @input="handleVolumeChange"
          class="volume-range"
          aria-label="音量"
        >
      </div>
    </div>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'

const props = defineProps({
  volume: Number,
  muted: Boolean,
  volumeIcon: String
})

const emit = defineEmits(['toggle-mute', 'volume-change'])

const handleVolumeChange = (event) => {
  const newVolume = parseInt(event.target.value)
  emit('volume-change', newVolume)
}
</script>

<style scoped>
.volume-control {
  @apply flex items-center gap-2;
}

.control-btn {
  @apply p-2 rounded-lg bg-black/20 hover:bg-black/40 
    transition-colors duration-200 text-white
    focus:outline-none focus:ring-2 focus:ring-white/50;
}

.control-icon {
  @apply text-lg;
}

.volume-slider-container {
  @apply w-20 opacity-0 group-hover:opacity-100 transition-opacity duration-200;
}

.volume-slider-wrapper {
  @apply relative flex items-center h-6;
}

.volume-track-bg {
  @apply absolute w-full h-1 bg-white/20 rounded-full;
}

.volume-range-fill {
  @apply absolute h-1 bg-white rounded-full transition-all duration-200;
}

.volume-range {
  @apply absolute w-full h-6 opacity-0 cursor-pointer;
  -webkit-appearance: none;
  appearance: none;
}

.volume-range::-webkit-slider-thumb {
  @apply w-3 h-3 rounded-full bg-white border-0 cursor-pointer;
  -webkit-appearance: none;
  appearance: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.volume-range::-moz-range-thumb {
  @apply w-3 h-3 rounded-full bg-white border-0 cursor-pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

/* 触摸设备优化 */
@media (hover: none), (pointer: coarse) {
  .volume-slider-container {
    @apply w-5 opacity-100;
  }
  
  .volume-range::-webkit-slider-thumb {
    @apply w-4 h-4;
  }
  
  .volume-range::-moz-range-thumb {
    @apply w-4 h-4;
  }
}
</style>
