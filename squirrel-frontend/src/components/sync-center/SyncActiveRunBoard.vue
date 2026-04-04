<template>
  <section class="board-shell board-shell--active">
    <div class="board-header">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <p class="board-kicker">LANE_02</p>
          <div class="h-px flex-1 bg-white/5"></div>
          <span class="board-count font-mono">{{ items.length.toString().padStart(2, '0') }}</span>
        </div>
        <h2 class="board-title">ACTIVE_PROCESSING</h2>
      </div>
    </div>

    <div v-if="items.length" class="worker-strip" aria-hidden="true">
      <div
        v-for="(item, index) in items"
        :key="item.run_id || item.subscription_id"
        class="worker-pill"
      >
        <span class="worker-pill__dot"></span>
        <span class="worker-pill__label">{{ pipeline === 'extract' ? `Batch ${index + 1}` : `Worker ${index + 1}` }}</span>
        <span class="worker-pill__phase">{{ getPhaseLabel(item.current_phase) }}</span>
      </div>
    </div>

    <div v-if="error" class="board-error">{{ error }}</div>
    <div v-else-if="loading && !items.length" class="board-empty">正在获取运行中的订阅...</div>
    <div v-else-if="!items.length" class="board-empty">
      <div class="board-empty__content">
        <p>{{ emptyMessage }}</p>
        <p v-if="pipeline === 'feed' && carryoverCount > 0" class="board-empty__hint">
          其中 {{ carryoverCount }} 个订阅已转入“视频提取”tab。
        </p>
      </div>
    </div>

    <TransitionGroup v-else name="lane-card" tag="div" class="board-list">
      <button
        v-for="(item, index) in items"
        :key="item.run_id || item.subscription_id"
        type="button"
        class="run-row"
        @click="emit('open-run', item)"
      >
        <div class="run-row__main">
          <div class="run-row__identity">
            <div class="relative">
              <img
                :src="getAvatarSrc(item.subscription_avatar, item.subscription_id)"
                :alt="item.subscription_name"
                class="run-row__avatar"
                referrerpolicy="no-referrer"
                @error="(event) => handleAvatarError(event, item.subscription_id)"
              >
              <div class="absolute -top-0.5 -left-0.5 w-1.5 h-1.5 rounded-full bg-[#FFB300] glow-amber"></div>
            </div>
            <div class="min-w-0 flex-1">
              <div class="run-row__title">
                <h3 class="truncate text-sm font-bold text-white/90">{{ item.subscription_name }}</h3>
                <span class="phase-chip font-mono uppercase">{{ getPhaseLabel(item.current_phase) }}</span>
              </div>
              <p class="run-row__meta font-mono">
                {{ getMetaText(item) }}
              </p>
            </div>
          </div>

          <div class="run-row__progress">
            <span class="run-row__label font-mono">{{ item.progress_label || 'ACTIVE' }}</span>
          </div>
        </div>

        <!-- 离散能量条 (Power Bar) -->
        <div class="flex gap-1 h-1 w-full bg-white/5 mt-3">
          <div 
            v-for="i in 12" :key="i"
            class="flex-1 transition-colors duration-300"
            :class="i / 12 <= ((item.progress_percent || 0) / 100) ? 'bg-[#FF4F00]' : 'bg-transparent'"
          ></div>
        </div>

        <div v-if="pipeline === 'extract' || getFeedMetrics(item).length" class="metric-inline mt-3">
          <template v-if="pipeline === 'extract'">
            <div class="metric-group">
              <span class="metric-label">TOTAL</span>
              <span class="metric-value font-mono">{{ item.batch_task_count }}</span>
            </div>
            <div class="metric-group">
              <span class="metric-label">QUEUED</span>
              <span class="metric-value font-mono">{{ item.queued_task_count }}</span>
            </div>
            <div class="metric-group">
              <span class="metric-label">ACTIVE</span>
              <span class="metric-value font-mono text-[#FFB300]">{{ item.running_task_count }}</span>
            </div>
            <div class="metric-group">
              <span class="metric-label">DONE</span>
              <span class="metric-value font-mono text-[#00FF41]">{{ item.completed_task_count }}</span>
            </div>
          </template>
          <template v-else>
            <div
              v-for="metric in getFeedMetrics(item)"
              :key="`${item.run_id || item.subscription_id}-${metric.label}`"
              class="metric-group"
            >
              <span class="metric-label uppercase">{{ metric.label }}</span>
              <span 
                class="metric-value font-mono"
                :class="metric.tone === 'pending' ? 'text-[#FFB300]' : metric.tone === 'warn' ? 'text-rose-500' : ''"
              >
                {{ metric.value }}
              </span>
            </div>
          </template>
        </div>
      </button>
    </TransitionGroup>
  </section>
</template>

<script setup lang="ts">
import type { SyncCenterItem } from '@/composables/useSyncCenter'
import { useImageFallback } from '@/composables/useImageFallback'
import { formatDate } from '@/utils/dateFormat'

const props = withDefaults(defineProps<{
  items: SyncCenterItem[]
  loading: boolean
  error: string
  slotCount?: number
  pipeline?: 'feed' | 'extract'
  carryoverCount?: number
}>(), {
  pipeline: 'feed',
  carryoverCount: 0,
})

const emit = defineEmits<{
  (e: 'open-run', item: SyncCenterItem): void
}>()

const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback()
const boardCaption = props.pipeline === 'extract'
  ? '按最早开始时间稳定排序。每一行是一个真实活跃提取批次。'
  : '按最早开始时间稳定排序。每一行就是一个真实活跃 worker。'
const emptyMessage = props.pipeline === 'extract'
  ? '当前没有正在提取的视频批次'
  : props.carryoverCount > 0
    ? '当前没有列表拉取中的订阅'
    : '当前没有正在爬取的订阅'
const displayCountLabel = props.pipeline === 'feed' && props.carryoverCount > 0
  ? `${props.items.length} 项拉取中 · ${props.carryoverCount} 项转提取`
  : `${props.items.length} 项`

type MetricTone = 'default' | 'pending' | 'warn'

interface FeedMetric {
  label: string
  value: number
  tone?: MetricTone
}

const getPhaseLabel = (phase: string | null) => {
  switch (phase) {
    case 'fetching_feed': return '拉列表'
    case 'calculating_delta': return '计算增量'
    case 'enqueueing': return '派发提取'
    case 'queued': return '等待提取'
    case 'extracting': return '提取中'
    case 'finalizing': return '收尾中'
    case 'completed': return '已完成'
    default: return '运行中'
  }
}

const getTimeMetaText = (item: SyncCenterItem) => {
  if (item.locked_at) {
    return `开始于 ${formatDate(item.locked_at)}`
  }
  if (item.updated_at) {
    return `最近更新 ${formatDate(item.updated_at)}`
  }
  if (item.last_sync_at) {
    return `最近更新 ${formatDate(item.last_sync_at)}`
  }
  return '最近更新 --'
}

const getMetaText = (item: SyncCenterItem) => {
  const timestamp = getTimeMetaText(item)
  if (props.pipeline === 'extract') {
    return `${item.site || 'unknown'} · ${timestamp}`
  }

  if (item.current_phase === 'fetching_feed') {
    return `正在拉取视频列表 · ${timestamp}`
  }
  if (item.current_phase === 'calculating_delta') {
    return `正在计算增量结果 · ${timestamp}`
  }
  if (item.current_phase === 'enqueueing') {
    return `正在派发提取任务 · ${timestamp}`
  }
  return `最近更新 · ${timestamp}`
}

const getFeedMetrics = (item: SyncCenterItem): FeedMetric[] => {
  const pendingDispatch = Math.max(item.videos_found - item.videos_enqueued - item.videos_skipped, 0)
  const metrics: FeedMetric[] = []

  if (item.videos_found > 0) {
    metrics.push({ label: '累计发现', value: item.videos_found })
  }

  if (item.current_phase === 'enqueueing' && pendingDispatch > 0) {
    metrics.push({ label: '待派发', value: pendingDispatch, tone: 'pending' })
  }

  if (item.videos_skipped > 0) {
    metrics.push({ label: '累计跳过', value: item.videos_skipped })
  }

  if (item.current_phase === 'enqueueing' && item.videos_enqueued > 0) {
    metrics.push({ label: '累计已派发', value: item.videos_enqueued, tone: 'pending' })
  }

  return metrics
}
</script>

<style scoped>
.board-shell {
  border: 1px solid var(--cyber-border);
  background: rgba(255, 255, 255, 0.02);
  border-radius: 0;
  padding: 1.2rem;
  backdrop-filter: blur(8px);
  min-height: 0;
}

.board-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.2rem;
  border-left: 2px solid var(--cyber-amber);
  padding-left: 0.75rem;
}

.board-kicker {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.25em;
  text-transform: uppercase;
  color: var(--cyber-amber);
  opacity: 0.7;
}

.board-title {
  margin-top: 0.2rem;
  font-size: 1.1rem;
  font-weight: 900;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.95);
}

.board-caption {
  margin-top: 0.4rem;
  max-width: 22rem;
  font-size: 10px;
  line-height: 1.5;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: rgba(255, 255, 255, 0.3);
}

.board-count {
  font-size: 10px;
  font-weight: 800;
  font-family: 'JetBrains Mono', monospace;
  color: var(--cyber-amber);
  opacity: 0.5;
}

.worker-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.worker-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  border: 1px solid rgba(255, 179, 0, 0.15);
  background: rgba(255, 179, 0, 0.05);
  padding: 0.35rem 0.65rem;
}

.worker-pill__dot {
  width: 0.35rem;
  height: 0.35rem;
  border-radius: 9999px;
  background: var(--cyber-amber);
  box-shadow: 0 0 8px var(--cyber-amber);
  animation: worker-pulse 1.5s ease-in-out infinite;
}

.worker-pill__label,
.worker-pill__phase {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-family: 'JetBrains Mono', monospace;
}

.worker-pill__label {
  color: rgba(255, 255, 255, 0.3);
}

.worker-pill__phase {
  color: var(--cyber-amber);
  opacity: 0.8;
}

.board-empty,
.board-error {
  display: flex;
  min-height: 12rem;
  align-items: center;
  justify-content: center;
  border-radius: 0;
  border: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(255, 255, 255, 0.01);
  color: rgba(255, 255, 255, 0.25);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.board-error {
  color: rgba(251, 113, 133, 0.8);
  border-color: rgba(251, 113, 133, 0.2);
}

.board-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  max-height: calc(100vh - 18rem);
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.run-row {
  display: flex;
  flex-direction: column;
  width: 100%;
  background: #050505;
  padding: 0.85rem 1rem;
  text-align: left;
  transition: all 0.2s ease;
  border: none;
}

.run-row:hover {
  background: rgba(255, 255, 255, 0.03);
}

.run-row__main {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 0.75rem;
}

.run-row__identity {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  min-width: 0;
  flex: 1;
}

.run-row__avatar {
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 0;
  object-fit: cover;
  border: 1px solid rgba(255, 255, 255, 0.1);
  filter: grayscale(0.2);
}

.run-row__title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.run-row__meta {
  margin-top: 0.2rem;
  font-size: 10px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.3);
  text-transform: uppercase;
  letter-spacing: 0.02em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.run-row__progress {
  display: flex;
  align-items: end;
  flex-shrink: 0;
}

.run-row__label {
  font-size: 9px;
  font-weight: 900;
  color: var(--cyber-amber);
  opacity: 0.8;
  letter-spacing: 0.1em;
}

.phase-chip {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--cyber-amber);
  background: rgba(255, 179, 0, 0.1);
  padding: 0.05rem 0.35rem;
  font-size: 8px;
  font-weight: 900;
  color: var(--cyber-amber);
  letter-spacing: 0.05em;
  flex-shrink: 0;
}

.metric-inline {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.metric-group {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.metric-label {
  font-size: 7px;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.2);
  letter-spacing: 0.2em;
}

.metric-value {
  font-size: 11px;
  font-weight: 800;
  color: rgba(255, 255, 255, 0.6);
}

.lane-card-enter-active,
.lane-card-leave-active,
.lane-card-move {
  transition: all 0.2s ease;
}

.lane-card-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.lane-card-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@keyframes worker-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(0.8); opacity: 0.6; }
}
</style>
