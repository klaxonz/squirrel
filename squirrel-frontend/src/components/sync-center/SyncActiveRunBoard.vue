<template>
  <section class="board-shell board-shell--active">
    <div class="board-header">
      <div>
        <p class="board-kicker">Lane 02</p>
        <h2 class="board-title">当前正在处理</h2>
        <p class="board-caption">{{ boardCaption }}</p>
      </div>
      <span class="board-count">{{ displayCountLabel }}</span>
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
            <span class="run-row__worker">{{ pipeline === 'extract' ? `B${index + 1}` : `W${index + 1}` }}</span>
            <img
              :src="getAvatarSrc(item.subscription_avatar, item.subscription_id)"
              :alt="item.subscription_name"
              class="run-row__avatar"
              referrerpolicy="no-referrer"
              @error="(event) => handleAvatarError(event, item.subscription_id)"
            >
            <div class="min-w-0 flex-1">
              <div class="run-row__title">
                <h3 class="truncate text-sm font-semibold text-white/92">{{ item.subscription_name }}</h3>
                <span class="phase-chip">{{ getPhaseLabel(item.current_phase) }}</span>
              </div>
              <p class="run-row__meta">
                {{ getMetaText(item) }}
              </p>
            </div>
          </div>

          <div class="run-row__progress">
            <span class="run-row__label">{{ item.progress_label || '进行中' }}</span>
          </div>
        </div>

        <div v-if="pipeline === 'extract' || getFeedMetrics(item).length" class="metric-inline">
          <template v-if="pipeline === 'extract'">
            <span class="metric-pill">总数 {{ item.batch_task_count }}</span>
            <span class="metric-pill">排队 {{ item.queued_task_count }}</span>
            <span class="metric-pill">运行 {{ item.running_task_count }}</span>
            <span class="metric-pill metric-pill--pending">完成 {{ item.completed_task_count }}</span>
            <span v-if="item.failed_task_count" class="metric-pill metric-pill--warn">失败 {{ item.failed_task_count }}</span>
          </template>
          <template v-else>
            <span
              v-for="metric in getFeedMetrics(item)"
              :key="`${item.run_id || item.subscription_id}-${metric.label}`"
              class="metric-pill"
              :class="metric.tone === 'pending' ? 'metric-pill--pending' : metric.tone === 'warn' ? 'metric-pill--warn' : ''"
            >
              {{ metric.label }} {{ metric.value }}
            </span>
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
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(180deg, rgba(255, 160, 120, 0.08), rgba(255, 255, 255, 0.02) 22%, rgba(0, 0, 0, 0.44));
  border-radius: 1.5rem;
  padding: 1.2rem;
  backdrop-filter: blur(12px);
  min-height: 0;
}

.board-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.9rem;
}

.board-kicker {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: rgba(255, 188, 150, 0.64);
}

.board-title {
  margin-top: 0.28rem;
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: -0.04em;
  color: rgba(255, 255, 255, 0.94);
}

.board-caption {
  margin-top: 0.28rem;
  max-width: 22rem;
  font-size: 12px;
  line-height: 1.45;
  color: rgba(255, 255, 255, 0.44);
}

.board-count {
  font-size: 11px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.44);
}

.worker-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-bottom: 0.85rem;
}

.worker-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  border-radius: 9999px;
  border: 1px solid rgba(255, 178, 122, 0.22);
  background: rgba(255, 178, 122, 0.08);
  padding: 0.35rem 0.6rem;
}

.worker-pill__dot {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 9999px;
  background: rgba(255, 192, 120, 0.96);
  box-shadow: 0 0 10px rgba(255, 192, 120, 0.48);
  animation: worker-pulse 1.4s ease-in-out infinite;
}

.worker-pill__label,
.worker-pill__phase {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.worker-pill__label {
  color: rgba(255, 255, 255, 0.66);
}

.worker-pill__phase {
  color: rgba(255, 224, 188, 0.82);
}

.board-empty,
.board-error {
  display: flex;
  min-height: 12rem;
  align-items: center;
  justify-content: center;
  border-radius: 1rem;
  border: 1px dashed rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.42);
  font-size: 12px;
  font-weight: 600;
}

.board-error {
  color: rgba(251, 113, 133, 0.86);
}

.board-empty__content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.45rem;
}

.board-empty__hint {
  font-size: 11px;
  color: rgba(255, 196, 140, 0.78);
}

.board-list {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  max-height: calc(100vh - 18rem);
  overflow-y: auto;
  padding-right: 0.15rem;
}

.run-row {
  width: 100%;
  border-radius: 1.05rem;
  border: 1px solid rgba(255, 255, 255, 0.07);
  background: rgba(255, 255, 255, 0.025);
  padding: 0.8rem 0.85rem;
  text-align: left;
  transition: background-color 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
}

.run-row:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 171, 102, 0.26);
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
  gap: 0.65rem;
  min-width: 0;
  flex: 1;
}

.run-row__worker {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.8rem;
  background: rgba(255, 171, 102, 0.14);
  color: rgba(255, 221, 192, 0.92);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.run-row__avatar {
  width: 2rem;
  height: 2rem;
  border-radius: 0.8rem;
  object-fit: cover;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.run-row__title {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
}

.run-row__meta {
  margin-top: 0.16rem;
  font-size: 11px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.4);
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
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 192, 140, 0.74);
}

.phase-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 9999px;
  border: 1px solid rgba(255, 171, 102, 0.2);
  background: rgba(255, 171, 102, 0.08);
  padding: 0.12rem 0.4rem;
  font-size: 10px;
  font-weight: 700;
  color: rgba(255, 222, 195, 0.82);
  flex-shrink: 0;
}

.metric-inline {
  display: flex;
  flex-wrap: wrap;
  gap: 0.38rem;
  margin-top: 0.65rem;
}

.metric-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.04);
  padding: 0.24rem 0.5rem;
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.6);
}

.metric-pill--pending {
  background: rgba(255, 171, 102, 0.08);
  color: rgba(255, 212, 171, 0.92);
}

.metric-pill--warn {
  background: rgba(251, 113, 133, 0.1);
  color: rgba(255, 211, 219, 0.92);
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
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
  }

  50% {
    transform: scale(0.72);
    opacity: 0.52;
  }
}
</style>
