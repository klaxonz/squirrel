<template>
  <div v-if="visible" class="sp-stats-overlay" @click.stop>
    <div class="sp-stats-header">Stats for nerds</div>
    <div class="sp-stats-grid">
      <div class="sp-stats-row">
        <span class="sp-stats-label">Resolution</span>
        <span class="sp-stats-value">{{ resolutionText }}</span>
      </div>
      <div class="sp-stats-row">
        <span class="sp-stats-label">Codec</span>
        <span class="sp-stats-value">{{ stats.codec || '—' }}</span>
      </div>
      <div class="sp-stats-row">
        <span class="sp-stats-label">Source</span>
        <span class="sp-stats-value">{{ stats.sourceType || '—' }}</span>
      </div>
      <div class="sp-stats-row">
        <span class="sp-stats-label">Buffer Health</span>
        <span class="sp-stats-value">{{ stats.bufferedPercent.toFixed(1) }}%</span>
      </div>
      <div class="sp-stats-row">
        <span class="sp-stats-label">Speed</span>
        <span class="sp-stats-value">{{ stats.playbackRate }}x</span>
      </div>
      <div class="sp-stats-row">
        <span class="sp-stats-label">Volume</span>
        <span class="sp-stats-value">{{ stats.muted ? 'Muted' : Math.round(stats.volume) + '%' }}</span>
      </div>
      <div class="sp-stats-row">
        <span class="sp-stats-label">Position</span>
        <span class="sp-stats-value">{{ formatTime(stats.currentTime) }} / {{ formatTime(stats.duration) }}</span>
      </div>
      <div v-if="stats.totalFrames > 0" class="sp-stats-row">
        <span class="sp-stats-label">Dropped Frames</span>
        <span class="sp-stats-value">{{ stats.droppedFrames }} / {{ stats.totalFrames }} ({{ droppedPercent }}%)</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { formatTime } from '@/shared/lib/dateFormat'
import type { PlayerStats } from './core/types'

const props = defineProps<{
  getStats: () => PlayerStats
  visible?: boolean
}>()

const stats = ref<PlayerStats>({
  resolution: null,
  codec: null,
  sourceType: null,
  bufferedPercent: 0,
  playbackRate: 1,
  quality: null,
  volume: 100,
  muted: false,
  duration: 0,
  currentTime: 0,
  droppedFrames: 0,
  totalFrames: 0,
  videoBitrate: null,
  audioBitrate: null,
})

const resolutionText = computed(() => {
  const r = stats.value.resolution
  if (!r) return '—'
  return `${r.width}x${r.height}`
})

const droppedPercent = computed(() => {
  if (stats.value.totalFrames === 0) return 0
  return ((stats.value.droppedFrames / stats.value.totalFrames) * 100).toFixed(1)
})

let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  pollTimer = setInterval(() => {
    stats.value = props.getStats()
  }, 500)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.sp-stats-overlay {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 80;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  padding: 10px 14px;
  min-width: 220px;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.9);
  pointer-events: auto;
  user-select: text;
}

.sp-stats-header {
  font-size: 12px;
  font-weight: 700;
  color: var(--sp-primary, #d3d4d8);
  margin-bottom: 6px;
  letter-spacing: 0.05em;
}

.sp-stats-grid {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sp-stats-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.sp-stats-label {
  color: rgba(255, 255, 255, 0.5);
  flex-shrink: 0;
}

.sp-stats-value {
  color: rgba(255, 255, 255, 0.85);
  text-align: right;
}
</style>
