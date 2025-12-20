<template>
  <Icon 
    :icon="iconName"
    :class="['sp-icon', `sp-icon-${name}`]"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Icon } from '@iconify/vue'
import type { IconName } from './core/useIcons'

const props = defineProps<{
  name: IconName
}>()

// 图标名称映射：从我们的 IconName 映射到 Material Symbols
const iconMap: Record<IconName, string> = {
  play: 'material-symbols:play-arrow',
  pause: 'material-symbols:pause',
  stop: 'material-symbols:stop',
  replay: 'material-symbols:replay',
  skipForward: 'material-symbols:skip-next',
  skipBackward: 'material-symbols:skip-previous',
  previous: 'material-symbols:skip-previous',
  next: 'material-symbols:skip-next',
  volumeHigh: 'material-symbols:volume-up',
  volumeLow: 'material-symbols:volume-down',
  volumeMute: 'material-symbols:volume-mute',
  volumeOff: 'material-symbols:volume-off',
  fullscreen: 'material-symbols:fullscreen',
  fullscreenExit: 'material-symbols:fullscreen-exit',
  widescreen: 'material-symbols:fit-screen',
  widescreenExit: 'material-symbols:fit-screen',
  pip: 'material-symbols:picture-in-picture-alt',
  pipExit: 'material-symbols:picture-in-picture-alt',
  settings: 'material-symbols:settings',
  subtitles: 'material-symbols:closed-caption',
  subtitlesOff: 'material-symbols:closed-caption-disabled',
  quality: 'material-symbols:high-quality',
  speed: 'material-symbols:speed',
  check: 'material-symbols:check',
  chevronLeft: 'material-symbols:chevron-left',
  chevronRight: 'material-symbols:chevron-right',
  close: 'material-symbols:close',
  error: 'material-symbols:error',
  loading: 'material-symbols:progress-activity'
}

const iconName = computed(() => iconMap[props.name] || 'material-symbols:help')
</script>
