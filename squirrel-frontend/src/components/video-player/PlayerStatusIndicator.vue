<template>
  <div class="status-indicator" v-if="showIndicator">
    <div class="status-content">
      <Icon :icon="statusIcon" class="status-icon" />
      <span class="status-text">{{ statusText }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Icon } from '@iconify/vue'

const props = defineProps({
  showIndicator: {
    type: Boolean,
    default: false
  },
  status: {
    type: String, // 'play', 'pause', 'mute', 'unmute', 'fullscreen', 'exit-fullscreen', 'theater', 'exit-theater'
    default: 'play'
  }
})

const statusIcon = computed(() => {
  const iconMap = {
    'play': 'material-symbols:play-arrow',
    'pause': 'material-symbols:pause',
    'mute': 'material-symbols:volume-off',
    'unmute': 'material-symbols:volume-up',
    'fullscreen': 'material-symbols:fullscreen',
    'exit-fullscreen': 'material-symbols:fullscreen-exit',
    'theater': 'material-symbols:fit-screen',
    'exit-theater': 'material-symbols:fit-screen'
  }
  return iconMap[props.status] || 'material-symbols:info'
})

const statusText = computed(() => {
  const textMap = {
    'play': '播放',
    'pause': '暂停',
    'mute': '静音',
    'unmute': '取消静音',
    'fullscreen': '全屏',
    'exit-fullscreen': '退出全屏',
    'theater': '剧场模式',
    'exit-theater': '退出剧场模式'
  }
  return textMap[props.status] || ''
})
</script>

<style scoped>
.status-indicator {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
    pointer-events-none z-30;
  animation: statusIndicatorShow 0.4s ease-out;
}

.status-content {
  @apply flex items-center gap-3 px-4 py-3 rounded-xl;
  background: var(--sp-overlay-strong);
  backdrop-filter: blur(12px);
  border: 1px solid var(--sp-border);
  box-shadow: var(--sp-shadow-lg);
}

.status-icon {
  @apply text-2xl;
  color: var(--sp-text);
  filter: drop-shadow(var(--sp-drop-shadow-md));
}

.status-text {
  @apply text-sm font-medium;
  color: var(--sp-text);
  font-family: var(--sp-font-family);
  text-shadow: var(--sp-text-shadow);
}

@keyframes statusIndicatorShow {
  0% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.8);
  }
  30% {
    transform: translate(-50%, -50%) scale(1.1);
    opacity: 1;
  }
  100% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}
</style>
