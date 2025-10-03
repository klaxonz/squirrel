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

    <!-- 上一个视频按钮 -->
    <button
      @click="$emit('prev-video')"
      class="vp-control-btn skip-video-btn"
      :disabled="!hasPrev"
      :class="{ 'disabled': !hasPrev }"
      aria-label="上一个视频"
      title="上一个视频"
    >
      <Icon icon="material-symbols:skip-previous" class="vp-control-icon" />
    </button>
    
    <!-- 下一个视频按钮 -->
    <button
      @click="$emit('next-video')"
      class="vp-control-btn skip-video-btn"
      :disabled="!hasNext"
      :class="{ 'disabled': !hasNext }"
      aria-label="下一个视频"
      title="下一个视频"
    >
      <Icon icon="material-symbols:skip-next" class="vp-control-icon" />
    </button>

    <!-- 快退10秒 -->
    <button
      @click="$emit('skip-backward')"
      class="vp-control-btn skip-btn"
      aria-label="后退10秒"
    >
      <Icon icon="material-symbols:replay-10" class="vp-control-icon" />
    </button>

    <!-- 快进10秒 -->
    <button
      @click="$emit('skip-forward')"
      class="vp-control-btn skip-btn"
      aria-label="前进10秒"
    >
      <Icon icon="material-symbols:forward-10" class="vp-control-icon" />
    </button>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'

const props = defineProps({
  playing: Boolean,
  hasPrev: { type: Boolean, default: false },
  hasNext: { type: Boolean, default: false }
})

const emit = defineEmits(['toggle-play', 'skip-forward', 'skip-backward', 'prev-video', 'next-video'])
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
  transition: all 0.15s ease;
}

.vp-control-btn:hover:not(.disabled) {
  transform: scale(1.05);
}

.vp-control-btn:active:not(.disabled) {
  transform: scale(0.98);
}

.play-btn {
  @apply p-2;
  min-width: 48px;
  min-height: 48px;
}

.skip-btn {
  @apply p-2;
  min-width: 36px;
  min-height: 36px;
}

.skip-video-btn {
  @apply p-2;
  min-width: 40px;
  min-height: 40px;
}

.skip-video-btn.disabled {
  opacity: 0.3;
  cursor: not-allowed;
  pointer-events: none;
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

.skip-video-btn .vp-control-icon {
  @apply text-xl;
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
