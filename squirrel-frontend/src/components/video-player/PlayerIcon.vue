<template>
  <component
    :is="iconComponent"
    :class="['sp-icon', `sp-icon-${name}`]"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  Play,
  Pause,
  Square,
  RotateCcw,
  SkipForward,
  SkipBack,
  Volume2,
  Volume1,
  VolumeX,
  VolumeOff,
  Maximize,
  Minimize,
  PictureInPicture2,
  PictureInPicture,
  Settings,
  Clapperboard,
  Subtitles,
  CaptionsOff,
  BadgeCheck,
  Gauge,
  CirclePlay,
  Repeat,
  Check,
  ChevronLeft,
  ChevronRight,
  X,
  AlertCircle,
  LoaderCircle,
  RectangleHorizontal,
} from 'lucide-vue-next'
import type { IconName } from './core/useIcons'

const props = defineProps<{
  name: IconName
}>()

const iconMap: Record<string, any> = {
  play: Play,
  pause: Pause,
  stop: Square,
  replay: RotateCcw,
  skipForward: SkipForward,
  skipBackward: SkipBack,
  previous: SkipBack,
  prev: SkipBack,
  next: SkipForward,
  volumeHigh: Volume2,
  volumeLow: Volume1,
  volumeMute: VolumeX,
  volumeOff: VolumeOff,
  fullscreen: Maximize,
  fullscreenExit: Minimize,
  widescreen: RectangleHorizontal, // 修正：宽屏使用横向矩形
  widescreenExit: Square,          // 修正：退出宽屏使用正方形
  pip: PictureInPicture2,
  pipExit: PictureInPicture,
  settings: Settings,
  markClip: Clapperboard,
  subtitles: Subtitles,
  subtitlesOff: CaptionsOff,
  quality: BadgeCheck,
  speed: Gauge,
  autoplayNext: CirclePlay,
  loop: Repeat,
  check: Check,
  chevronLeft: ChevronLeft,
  chevronRight: ChevronRight,
  close: X,
  error: AlertCircle,
  loading: LoaderCircle,
}

const iconComponent = computed(() => iconMap[props.name] || AlertCircle)
</script>

<style scoped>
.sp-icon {
  width: 100%;
  height: 100%;
}
</style>
