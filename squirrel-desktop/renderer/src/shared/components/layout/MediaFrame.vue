<template>
  <div
    class="app-media-frame"
    :class="[ratioClass, { 'app-media-frame--blur': blur, 'app-media-frame--square': square }]"
  >
    <slot />

    <span v-if="showScrim" class="app-media-frame__scrim" aria-hidden="true" />

    <slot name="overlay" />

    <slot name="badge">
      <span
        v-if="duration"
        class="app-media-duration-badge"
        :class="{ 'app-media-duration-badge--compact': compact }"
      >
        {{ duration }}
      </span>
    </slot>

    <div
      v-if="showProgress"
      class="app-media-progress"
      role="progressbar"
      :aria-label="progressLabel"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-valuenow="progressPercent"
    >
      <span class="app-media-progress__fill" :style="{ width: `${progressPercent}%` }" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

/**
 * Layout-only media frame. The image stays in the default slot so features
 * keep owning loading/fallback behavior (and tests keep mocking
 * VideoThumbnail by its original path).
 */
const props = withDefaults(defineProps<{
  /** CSS aspect ratio, e.g. `16:9`, `4:3`, `1:1`, `3:2`. */
  ratio?: '16:9' | '4:3' | '1:1' | '3:2'
  duration?: string
  /** 0–1 playback progress. Omit to hide the bar. */
  progress?: number | null
  progressLabel?: string
  blur?: boolean
  square?: boolean
  compact?: boolean
  showScrim?: boolean
}>(), {
  ratio: '16:9',
  duration: '',
  progress: null,
  progressLabel: '播放进度',
  blur: false,
  square: false,
  compact: false,
  showScrim: false,
})

const ratioClass = computed(() => (
  props.ratio === '16:9' ? '' : `app-media-frame--ratio-${props.ratio.replace(':', '-')}`
))

const showProgress = computed(() => (
  props.progress !== null
  && props.progress !== undefined
  && Number.isFinite(props.progress)
  && props.progress > 0
))

const progressPercent = computed(() => (
  Math.min(100, Math.max(0, Math.round((props.progress ?? 0) * 100)))
))
</script>
