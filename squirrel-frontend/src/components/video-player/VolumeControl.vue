<template>
  <div class="volume-control group">
    <button
      @click="$emit('toggle-mute')"
      class="vp-control-btn"
      :aria-label="muted ? '取消静音' : '静音'"
    >
      <Icon :icon="volumeIcon" class="vp-control-icon" />
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
  @apply flex items-center;
  gap: 4px;
}

/* 使用全局按钮样式，补充尺寸与动效 */
.vp-control-btn {
  @apply p-2 flex items-center justify-center;
  min-width: 40px;
  min-height: 40px;
}

.vp-control-btn:hover {
  transform: scale(1.05);
}

.vp-control-btn:active {
  transform: scale(0.98);
}

.vp-control-icon {
  @apply text-xl;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3));
}

.volume-slider-container {
  @apply opacity-0 group-hover:opacity-100 transition-all duration-300;
  width: 0;
  transform: translateX(-4px);
}

.group:hover .volume-slider-container {
  width: 80px;
}

.volume-slider-wrapper {
  @apply relative flex items-center;
  height: 32px;
  padding: 8px 0;
}

.volume-track-bg {
  @apply absolute w-full rounded-full;
  height: 3px;
  background: rgba(255, 255, 255, 0.3);
}

.volume-range-fill {
  @apply absolute rounded-full transition-all duration-200;
  height: 3px;
  background: #ffffff;
  box-shadow: 0 0 4px rgba(255, 255, 255, 0.2);
}

.volume-range {
  @apply absolute w-full opacity-0 cursor-pointer;
  height: 32px;
  background: transparent;
  -webkit-appearance: none;
  appearance: none;
}

.volume-range::-webkit-slider-thumb {
  @apply rounded-full cursor-pointer;
  width: 12px;
  height: 12px;
  background: #ffffff;
  border: none;
  -webkit-appearance: none;
  appearance: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  transition: all 0.2s ease;
}

.volume-range::-webkit-slider-thumb:hover {
  transform: scale(1.2);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4);
}

.volume-range::-moz-range-thumb {
  @apply rounded-full cursor-pointer;
  width: 12px;
  height: 12px;
  background: #ffffff;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  transition: all 0.2s ease;
}

.volume-range::-moz-range-thumb:hover {
  transform: scale(1.2);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4);
}

/* 悬停时显示音量滑块的动画 */
.volume-control:hover .volume-slider-container {
  @apply opacity-100;
  transform: translateX(0);
}

/* 触摸设备优化 */
@media (hover: none), (pointer: coarse) {
  .volume-slider-container {
    @apply opacity-100;
    width: 60px;
  }

  .volume-range::-webkit-slider-thumb {
    width: 16px;
    height: 16px;
  }

  .volume-range::-moz-range-thumb {
    width: 16px;
    height: 16px;
  }
}
</style>
