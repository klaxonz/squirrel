<template>
  <div v-if="visible" class="sp-stats-overlay" @click.stop>
    <div class="sp-stats-header">播放统计</div>
    <div class="sp-stats-grid">
      <div class="sp-stats-row">
        <span class="sp-stats-label">分辨率</span>
        <span class="sp-stats-value">{{ resolutionText }}</span>
      </div>
      <div class="sp-stats-row">
        <span class="sp-stats-label">编码</span>
        <span class="sp-stats-value">{{ stats.codec || '—' }}</span>
      </div>
      <div class="sp-stats-row">
        <span class="sp-stats-label">来源</span>
        <span class="sp-stats-value">{{ stats.sourceType || '—' }}</span>
      </div>
      <div class="sp-stats-row">
        <span class="sp-stats-label">缓冲</span>
        <span class="sp-stats-value">{{ stats.bufferedPercent.toFixed(1) }}%</span>
      </div>
      <div class="sp-stats-row">
        <span class="sp-stats-label">倍速</span>
        <span class="sp-stats-value">{{ stats.playbackRate }}x</span>
      </div>
      <div class="sp-stats-row">
        <span class="sp-stats-label">音量</span>
        <span class="sp-stats-value">{{ stats.muted ? '已静音' : Math.round(stats.volume) + '%' }}</span>
      </div>
      <div class="sp-stats-row">
        <span class="sp-stats-label">进度</span>
        <span class="sp-stats-value">{{ formatTime(stats.currentTime) }} / {{ formatTime(stats.duration) }}</span>
      </div>
      <div v-if="stats.totalFrames > 0" class="sp-stats-row">
        <span class="sp-stats-label">丢帧</span>
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
  width: min(248px, calc(100% - 20px));
  padding: 12px 14px;
  background: var(--sp-menu-bg);
  border: 1px solid var(--sp-menu-border);
  border-radius: var(--sp-radius-lg);
  box-shadow: var(--sp-menu-shadow);
  font-family: var(--sp-font-mono);
  font-size: 11px;
  color: rgba(255, 255, 255, 0.9);
  pointer-events: auto;
  user-select: text;
}

.sp-stats-header {
  color: var(--sp-text-strong);
  font-family: var(--sp-font-family);
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  letter-spacing: 0;
}

.sp-stats-grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sp-stats-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.sp-stats-label {
  color: var(--sp-text-muted);
  flex-shrink: 0;
}

.sp-stats-value {
  color: var(--sp-text-secondary);
  text-align: right;
}
</style>
