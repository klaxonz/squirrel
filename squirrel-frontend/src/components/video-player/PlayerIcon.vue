<template>
  <AppIcon
    :name="iconName"
    :class="['sp-icon', `sp-icon-${name}`]"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import type { AppIconName } from '@/icons/app-icons'
import type { IconName } from './core/useIcons'

const props = defineProps<{
  name: IconName
}>()

const iconMap: Record<IconName, AppIconName> = {
  play: 'play',
  pause: 'pause',
  stop: 'stop',
  replay: 'replay',
  rotate: 'rotate',
  skipForward: 'skipForward',
  skipBackward: 'skipBackward',
  previous: 'previous',
  prev: 'previous',
  next: 'next',
  volumeHigh: 'volumeHigh',
  volumeLow: 'volumeLow',
  volumeMute: 'volumeMute',
  volumeOff: 'volumeOff',
  fullscreen: 'fullscreen',
  fullscreenExit: 'fullscreenExit',
  widescreen: 'widescreen',
  widescreenExit: 'widescreenExit',
  pip: 'pip',
  pipExit: 'pipExit',
  settings: 'settingsPanel',
  markClip: 'markClip',
  subtitles: 'subtitles',
  subtitlesOff: 'subtitlesOff',
  quality: 'quality',
  speed: 'speed',
  autoplayNext: 'autoplayNext',
  loop: 'loop',
  check: 'check',
  chevronLeft: 'chevronLeft',
  chevronRight: 'chevronRight',
  close: 'close',
  error: 'error',
  loading: 'loading',
  screenshot: 'camera',
  sleepTimer: 'time',
  loopAB: 'loop',
  info: 'info',
}

const iconName = computed(() => iconMap[props.name] || 'error')
</script>

<style scoped>
.sp-icon {
  width: 100%;
  height: 100%;
}
</style>
