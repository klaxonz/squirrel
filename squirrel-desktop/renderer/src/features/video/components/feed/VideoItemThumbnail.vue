<template>
  <MediaFrame class="video-item__thumb" :class="`video-item__thumb--${variant}`">
    <VideoThumbnail :src="src" :alt="title" fit="cover" interactive :blur="blur" @error="emit('error')" />
    <span
      v-if="duration"
      class="video-item__duration app-mono"
      :class="{ 'video-item__duration--with-progress': progressRatio > 0 }"
    >
      {{ formatDuration(duration) }}
    </span>
    <div v-if="variant === 'grid'" class="video-item__scrim" />
    <div
      v-if="showProgress && progressRatio > 0"
      class="video-item__progress"
      role="progressbar"
      :aria-valuenow="progressPercent"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-label="`已观看 ${progressPercent}%`"
    >
      <div class="video-item__progress-fill" :style="{ width: `${progressRatio * 100}%` }" />
    </div>
  </MediaFrame>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatDuration } from '@/shared/lib/dateFormat'
import MediaFrame from '@/shared/components/layout/MediaFrame.vue'
import VideoThumbnail from './VideoThumbnail.vue'

const props = withDefaults(defineProps<{
  src: string
  title: string
  duration?: number | null
  progressRatio: number
  showProgress: boolean
  blur: boolean
  variant?: 'grid' | 'card' | 'row'
}>(), { variant: 'grid' })

const emit = defineEmits<{
  error: []
}>()

const progressPercent = computed(() => Math.round(props.progressRatio * 100))
</script>
