<template>
  <div class="playback-controls">
    <!-- 播放/暂停按钮 -->
    <button
      @click="$emit('toggle-play')"
      class="vp-control-btn play-btn"
      :aria-label="playing ? '暂停' : '播放'"
    >
      <Icon
        v-if="playing"
        icon="material-symbols:pause"
        class="vp-control-icon"
      />
      <Icon
        v-else
        icon="material-symbols:play-arrow"
        class="vp-control-icon"
      />
    </button>

    <!-- 跳过按钮组 -->
    <div class="skip-controls">
      <button
        @click="$emit('skip-backward')"
        class="vp-control-btn skip-btn"
        aria-label="后退10秒"
      >
        <Icon icon="material-symbols:replay-10" class="vp-control-icon" />
      </button>
      
      <button
        @click="$emit('skip-forward')"
        class="vp-control-btn skip-btn"
        aria-label="前进10秒"
      >
        <Icon icon="material-symbols:forward-10" class="vp-control-icon" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'

const props = defineProps({
  playing: Boolean
})

const emit = defineEmits(['toggle-play', 'skip-forward', 'skip-backward'])
</script>

<style scoped>
.playback-controls {
  @apply flex items-center;
  gap: 4px;
}

/* 统一使用全局样式的按钮外观 */
.vp-control-btn {
  @apply flex items-center justify-center;
  min-width: 40px;
  min-height: 40px;
}

.vp-control-btn:hover {
  transform: scale(1.05);
}

.vp-control-btn:active {
  transform: scale(0.98);
}

.play-btn {
  @apply p-2;
  min-width: 48px;
  min-height: 48px;
}

.skip-controls {
  @apply flex items-center;
  gap: 2px;
}

.skip-btn {
  @apply p-2;
  min-width: 36px;
  min-height: 36px;
}

.vp-control-icon {
  @apply text-lg;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3));
}

.play-btn .vp-control-icon {
  @apply text-2xl;
}

.skip-btn .vp-control-icon {
  @apply text-lg;
}

/* YouTube风格的播放按钮柔和光晕 */
.play-btn {
  position: relative;
}

.play-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.15s ease;
}

.play-btn:hover::before {
  opacity: 1;
}
</style>
