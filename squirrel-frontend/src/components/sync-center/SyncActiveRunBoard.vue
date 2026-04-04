<template>
  <section class="board-shell board-shell--active">
    <div class="board-header">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <p class="board-kicker">ACTIVE_PROCESSING</p>
          <div class="h-px flex-1 bg-white/5"></div>
          <span class="board-count font-mono">{{ items.length.toString().padStart(2, '0') }}</span>
        </div>
      </div>
    </div>

    <div v-if="error" class="board-error">{{ error }}</div>
    <div v-else-if="loading && !items.length">
      <SyncBoardSkeleton :count="11" />
    </div>
    <div v-else-if="!items.length">
      <SyncBoardEmpty 
        title="IDLE_STATE"
        :message="emptyMessage"
      >
        <template v-if="pipeline === 'feed' && carryoverCount > 0" #hint>
          <p class="text-[9px] font-bold text-white/10 mt-3 tracking-wide uppercase">
            其中 {{ carryoverCount }} 个订阅已转入“视频提取”tab
          </p>
        </template>
      </SyncBoardEmpty>
    </div>

    <TransitionGroup v-else name="lane-card" tag="div" class="board-list">
      <button
        v-for="(item, index) in items"
        :key="item.run_id || item.subscription_id"
        type="button"
        class="run-row animate-scan"
        @click="emit('open-run', item)"
      >
        <div class="run-row__main">
          <div class="run-row__identity">
            <SubscriptionAvatar
              :src="item.subscription_avatar"
              :name="item.subscription_name"
              size="md"
            />
            <div class="min-w-0 flex-1">
              <div class="run-row__title">
                <h3 class="truncate text-sm font-bold text-white/90">{{ item.subscription_name }}</h3>
              </div>
              <div class="run-row__meta run-row__meta--with-icon font-mono">
                <SiteIcon
                  v-if="item.site"
                  :icon-url="item.site_icon_url"
                  :label="item.site"
                  size="xs"
                  class="run-row__site-icon"
                />
                <span class="run-row__meta-text">{{ getMetaText(item) }}</span>
              </div>
            </div>
          </div>

          <div
            v-if="pipeline === 'extract' || getFeedMetrics(item).length"
            class="metric-inline"
            :class="pipeline === 'extract' ? 'metric-inline--compact' : ''"
          >
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
        </div>
      </button>
    </TransitionGroup>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import SiteIcon from '@/components/common/SiteIcon.vue'
import SyncBoardEmpty from '@/components/sync-center/SyncBoardEmpty.vue'
import SyncBoardSkeleton from '@/components/sync-center/SyncBoardSkeleton.vue'
import type { SyncCenterItem } from '@/composables/useSyncCenter'
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
    return `正在提取视频 · ${timestamp}`
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
  background: transparent;
  border-radius: 0;
  padding: 1.2rem;
  min-height: 0;
  border: none;
}

.board-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
  padding-left: 0.5rem;
}

.board-kicker {
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: var(--sci-fi-amber);
  opacity: 0.5;
}

.board-title {
  margin-top: 0.3rem;
  font-size: 1.25rem;
  font-weight: 900;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.8);
}

.board-count {
  font-size: 12px;
  font-weight: 900;
  font-family: 'JetBrains Mono', monospace;
  color: var(--sci-fi-amber);
  opacity: 0.8;
}

.board-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: calc(100vh - 18rem);
  overflow-y: auto;
}

.run-row {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 3.5rem;
  min-height: 3.5rem;
  background: transparent;
  padding: 0.6rem 1rem;
  text-align: left;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;
  position: relative;
}

.run-row:hover {
  transform: translateX(6px);
  background: rgba(255, 255, 255, 0.02);
}

.run-row__main {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 1rem;
}

.run-row__identity {
  display: flex;
  align-items: center;
  gap: 1rem;
  min-width: 0;
  flex: 1;
}

.run-row__meta {
  margin-top: 0.2rem;
  font-size: 9px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.25);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.run-row__title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.run-row__meta--with-icon {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  min-width: 0;
}

.run-row__site-icon {
  opacity: 0.72;
}

.run-row__meta-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.run-row__avatar {
  transition: all 0.3s ease;
}

.run-row:hover .run-row__avatar {
  transform: scale(1.1);
}

.metric-inline {
  display: flex;
  flex-direction: row;
  gap: 1.5rem;
  flex-shrink: 0;
  align-items: flex-end;
}

.metric-inline--compact {
  gap: 0.85rem;
}

.metric-group {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.metric-label {
  font-size: 6px;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.15);
  letter-spacing: 0.2em;
}

.metric-value {
  font-size: 12px;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.4);
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
