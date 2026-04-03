<template>
  <section class="board-shell board-shell--recent">
    <div class="board-header">
      <div>
        <p class="board-kicker">Lane 03</p>
        <h2 class="board-title">刚处理完</h2>
        <p class="board-caption">按最新拉取收口时间倒序。包含已转提取和终态结果，最上面就是刚从中列流出的最新 run。</p>
        <p class="board-updated">最近更新 {{ lastUpdatedAt || '--' }}</p>
      </div>
      <span class="board-count">近 {{ displayRuns.length }} 条</span>
    </div>

    <div v-if="error" class="board-error">{{ error }}</div>
    <div v-else-if="loading && !displayRuns.length" class="board-empty">正在加载最近运行结果...</div>
    <div v-else-if="!displayRuns.length" class="board-empty">当前没有最近运行结果</div>

    <TransitionGroup v-else name="lane-card" tag="div" class="board-list">
      <button
        v-for="(run, index) in displayRuns"
        :key="run.run_id"
        type="button"
        class="recent-row"
        :class="[
          selectedRunId === run.run_id ? 'recent-row--active' : '',
          index === 0 ? 'recent-row--latest' : '',
          freshRunIds.has(run.run_id) ? 'recent-row--fresh' : '',
        ]"
        @click="emit('open-run', run.run_id)"
      >
        <div class="recent-row__main">
          <div class="recent-row__identity">
            <img
              :src="getAvatarSrc(run.subscription_avatar, run.run_id)"
              :alt="run.subscription_name"
              class="recent-row__avatar"
              referrerpolicy="no-referrer"
              @error="(event) => handleAvatarError(event, run.run_id)"
            >

            <div class="min-w-0 flex-1">
            <div class="recent-row__title">
              <span class="status-chip" :class="getStatusChipClass(run.status)">
                {{ getStatusLabel(run.status) }}
              </span>
              <span v-if="index === 0" class="latest-chip">最新</span>
              <span v-if="freshRunIds.has(run.run_id)" class="fresh-chip">刚更新</span>
              <h3 class="truncate text-sm font-semibold text-white/92">{{ run.subscription_name }}</h3>
            </div>
            <p class="recent-row__meta">
              {{ getPhaseLabel(run.current_phase) }} · {{ run.site || 'unknown' }} · {{ getMetaTimestamp(run) }}
            </p>
            </div>
          </div>

          <div class="recent-row__summary">
            <span class="recent-row__percent">{{ run.progress_percent }}%</span>
          </div>
        </div>

        <div class="metric-inline">
          <span class="metric-pill">发现 {{ run.videos_found }}</span>
          <span class="metric-pill">入队 {{ run.videos_enqueued }}</span>
          <span class="metric-pill">提取 {{ run.videos_extracted }}</span>
          <span class="metric-pill" :class="run.pending_video_count ? 'metric-pill--warn' : ''">
            剩余 {{ run.pending_video_count }}
          </span>
        </div>
      </button>
    </TransitionGroup>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { SyncRunItem } from '@/composables/useSyncHistory'
import { useImageFallback } from '@/composables/useImageFallback'
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

const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback()
const displayRuns = computed(() => props.runs.slice(0, 8))
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
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(180deg, rgba(126, 182, 255, 0.08), rgba(255, 255, 255, 0.02) 22%, rgba(0, 0, 0, 0.44));
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
  color: rgba(157, 209, 255, 0.66);
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
  max-width: 20rem;
  font-size: 12px;
  line-height: 1.45;
  color: rgba(255, 255, 255, 0.44);
}

.board-updated {
  margin-top: 0.32rem;
  font-size: 11px;
  font-weight: 600;
  color: rgba(126, 182, 255, 0.74);
}

.board-count {
  font-size: 11px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.44);
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

.board-list {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  max-height: calc(100vh - 18rem);
  overflow-y: auto;
  padding-right: 0.15rem;
}

.recent-row {
  width: 100%;
  border-radius: 1rem;
  border: 1px solid rgba(255, 255, 255, 0.07);
  background: rgba(255, 255, 255, 0.025);
  padding: 0.8rem 0.85rem;
  text-align: left;
  transition: border-color 0.18s ease, background-color 0.18s ease, transform 0.18s ease;
}

.recent-row:hover {
  transform: translateY(-1px);
  border-color: rgba(126, 182, 255, 0.24);
  background: rgba(255, 255, 255, 0.04);
}

.recent-row--latest {
  border-color: rgba(126, 182, 255, 0.26);
}

.recent-row--fresh {
  border-color: rgba(96, 165, 250, 0.42);
  background: rgba(96, 165, 250, 0.08);
  box-shadow: 0 0 0 1px rgba(96, 165, 250, 0.12);
}

.recent-row--active {
  border-color: rgba(126, 182, 255, 0.34);
  background: rgba(126, 182, 255, 0.08);
}

.recent-row__main {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 0.75rem;
}

.recent-row__identity {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  min-width: 0;
  flex: 1;
}

.recent-row__avatar {
  width: 2rem;
  height: 2rem;
  border-radius: 0.8rem;
  object-fit: cover;
  flex-shrink: 0;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
}

.recent-row__title {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
}

.recent-row__meta {
  margin-top: 0.18rem;
  font-size: 11px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.4);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recent-row__summary {
  display: flex;
  align-items: start;
  flex-shrink: 0;
}

.recent-row__percent {
  font-size: 1rem;
  font-weight: 700;
  line-height: 1;
  color: rgba(255, 255, 255, 0.9);
}

.status-chip,
.latest-chip,
.fresh-chip,
.metric-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 9999px;
  font-size: 10px;
  font-weight: 700;
}

.status-chip {
  padding: 0.14rem 0.42rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.status-chip--success {
  border-color: rgba(74, 222, 128, 0.18);
  background: rgba(74, 222, 128, 0.1);
  color: rgba(190, 255, 212, 0.92);
}

.status-chip--failed {
  border-color: rgba(251, 113, 133, 0.18);
  background: rgba(251, 113, 133, 0.1);
  color: rgba(255, 203, 213, 0.92);
}

.status-chip--handoff {
  border-color: rgba(255, 187, 92, 0.22);
  background: rgba(255, 187, 92, 0.1);
  color: rgba(255, 229, 196, 0.92);
}

.status-chip--neutral {
  border-color: rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.68);
}

.latest-chip {
  padding: 0.14rem 0.4rem;
  background: rgba(126, 182, 255, 0.12);
  color: rgba(202, 227, 255, 0.92);
}

.fresh-chip {
  padding: 0.14rem 0.4rem;
  background: rgba(96, 165, 250, 0.16);
  color: rgba(219, 234, 254, 0.96);
}

.metric-inline {
  display: flex;
  flex-wrap: wrap;
  gap: 0.38rem;
  margin-top: 0.62rem;
}

.metric-pill {
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.62);
  padding: 0.22rem 0.48rem;
}

.metric-pill--warn {
  background: rgba(251, 113, 133, 0.08);
  color: rgba(255, 210, 218, 0.92);
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
