<template>
  <section class="board-shell board-shell--recent">
    <div class="board-header">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <p class="board-kicker">最近运行</p>
          <div class="h-px flex-1 bg-white/5"></div>
          <span class="board-count font-mono">{{ displayRuns.length.toString().padStart(2, '0') }}</span>
        </div>
      </div>
    </div>

    <div v-if="error" class="board-error">{{ error }}</div>
    <div v-else-if="loading && !displayRuns.length">
      <SyncBoardSkeleton :count="11" />
    </div>
    <div v-else-if="!displayRuns.length">
      <SyncBoardEmpty
        title="历史记录为空"
        message="当前没有最近运行结果"
      />
    </div>

    <TransitionGroup v-else name="lane-card" tag="div" class="board-list">
      <button
        v-for="(run, index) in displayRuns"
        :key="run.run_id"
        type="button"
        class="recent-row animate-scan"
        :class="[
          selectedRunId === run.run_id ? 'recent-row--active' : '',
          freshRunIds.has(run.run_id) ? 'recent-row--fresh' : '',
        ]"
        @click="emit('open-run', run.run_id)"
      >
        <div class="recent-row__main">
          <div class="recent-row__identity">
            <SubscriptionAvatar
              :src="run.subscription_avatar"
              :name="run.subscription_name"
              size="md"
            />

            <div class="min-w-0 flex-1">
              <div class="recent-row__title">
                <h3 class="truncate text-sm font-bold text-white/70">{{ run.subscription_name }}</h3>
              </div>
              <div class="recent-row__meta font-mono inline-flex items-center gap-1.5 mt-1">
                <SiteIcon
                  v-if="run.site"
                  :icon-url="run.site_icon_url"
                  :label="run.site"
                  size="xs"
                />
                <span>{{ getMetaTimestamp(run) }}</span>
              </div>
            </div>
          </div>

          <div class="metric-inline">
            <div class="metric-group">
              <span class="metric-label">发现</span>
              <span class="metric-value font-mono">{{ run.videos_found }}</span>
            </div>
            <div class="metric-group">
              <span class="metric-label">入队</span>
              <span class="metric-value font-mono">{{ run.videos_enqueued }}</span>
            </div>
            <div class="metric-group">
              <span class="metric-label">完成</span>
              <span class="metric-value font-mono">{{ run.videos_extracted }}</span>
            </div>
          </div>
        </div>
      </button>
    </TransitionGroup>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import SiteIcon from '@/components/common/SiteIcon.vue'
import SyncBoardEmpty from '@/components/sync-center/SyncBoardEmpty.vue'
import SyncBoardSkeleton from '@/components/sync-center/SyncBoardSkeleton.vue'
import type { SyncRunItem } from '@/composables/useSyncHistory'
import { formatDate } from '@/utils/dateFormat'

const props = withDefaults(defineProps<{
  runs: SyncRunItem[]
  loading: boolean
  error: string
  selectedRunId?: string
  lastUpdatedAt?: string
}>(), {
  selectedRunId: '',
  lastUpdatedAt: '',
})

const emit = defineEmits<{
  (e: 'open-run', runId: string): void
}>()

const displayRuns = computed(() => props.runs)
const freshRunIds = ref(new Set<string>())
const freshTimers = new Map<string, ReturnType<typeof setTimeout>>()
let previousRunIds: string[] = []

const markFresh = (runId: string) => {
  const next = new Set(freshRunIds.value)
  next.add(runId)
  freshRunIds.value = next

  const existingTimer = freshTimers.get(runId)
  if (existingTimer) {
    clearTimeout(existingTimer)
  }
  const timer = setTimeout(() => {
    const updated = new Set(freshRunIds.value)
    updated.delete(runId)
    freshRunIds.value = updated
    freshTimers.delete(runId)
  }, 12000)
  freshTimers.set(runId, timer)
}

watch(
  () => props.runs.map((run) => run.run_id),
  (runIds) => {
    if (!previousRunIds.length) {
      previousRunIds = [...runIds]
      return
    }

    runIds.forEach((runId, index) => {
      if (!runId) {
        return
      }
      const previousIndex = previousRunIds.indexOf(runId)
      if (previousIndex === -1 || previousIndex > index) {
        markFresh(runId)
      }
    })

    previousRunIds = [...runIds]
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  freshTimers.forEach((timer) => clearTimeout(timer))
  freshTimers.clear()
})

const getStatusLabel = (status: string) => {
  if (status === 'running') {
    return '已转提取'
  }
  switch (status) {
    case 'success': return '成功'
    case 'failed': return '失败'
    case 'queued': return '排队中'
    case 'deferred': return '已延后'
    case 'timeout': return '超时'
    default: return status || '未知'
  }
}

const getPhaseLabel = (phase: string | null) => {
  switch (phase) {
    case 'fetching_feed': return '拉列表'
    case 'calculating_delta': return '计算增量'
    case 'enqueueing': return '派发提取'
    case 'extracting': return '提取中'
    case 'finalizing': return '收尾中'
    case 'completed': return '已完成'
    default: return '未知阶段'
  }
}

const getMetaTimestamp = (run: SyncRunItem) => {
  if (run.feed_completed_at) {
    return `列表完成于 ${formatDate(run.feed_completed_at)}`
  }
  if (run.finished_at) {
    return `结束于 ${formatDate(run.finished_at)}`
  }
  return formatDate(run.last_event_at || run.started_at)
}

const getStatusChipClass = (status: string) => {
  if (status === 'running') {
    return 'status-chip--handoff'
  }
  switch (status) {
    case 'success': return 'status-chip--success'
    case 'failed': return 'status-chip--failed'
    case 'timeout': return 'status-chip--failed'
    default: return 'status-chip--neutral'
  }
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
  color: var(--sci-fi-green);
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
  color: var(--sci-fi-green);
  opacity: 0.8;
}

.board-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: calc(100vh - 18rem);
  overflow-y: auto;
}

.recent-row {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-height: 3.5rem;
  background: transparent;
  padding: 0.6rem 1rem;
  text-align: left;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;
  position: relative;
}

.recent-row:hover {
  transform: translateX(6px);
  background: rgba(255, 255, 255, 0.02);
}

.recent-row--active {
  background: oklch(75% 0.2 150 / 0.03);
  border-left: 2px solid var(--sci-fi-green);
}

.recent-row__main {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 1rem;
}

.recent-row__identity {
  display: flex;
  align-items: center;
  gap: 1rem;
  min-width: 0;
  flex: 1;
}

.recent-row__avatar {
  filter: grayscale(0.8) opacity(0.4);
  transition: all 0.3s ease;
}

.recent-row:hover .recent-row__avatar {
  filter: grayscale(0.2) opacity(0.8);
}

.recent-row__title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.recent-row__meta {
  margin-top: 0.2rem;
  font-size: 9px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.2);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.metric-inline {
  display: flex;
  flex-direction: row;
  gap: 1.5rem;
  flex-shrink: 0;
  align-items: flex-end;
}

.metric-group {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.metric-label {
  font-size: 7px;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.15);
  letter-spacing: 0.2em;
}

.metric-value {
  font-size: 14px;
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
</style>
