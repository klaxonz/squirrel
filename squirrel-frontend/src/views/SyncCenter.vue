<template>
  <div class="sync-center-page tactical-terminal min-h-full selection:bg-primary/10">
    <div class="matrix-bg"></div>
    <div class="toolbar-container py-8 relative z-10">
      <div class="flex flex-col gap-6">
        <SyncControlBar
          :auto-refresh="currentAutoRefresh"
          :can-reconcile="activePipeline === 'feed'"
          :can-retry-failed="retryTargetCount > 0"
          :last-updated-at="toolbarLastUpdatedAt"
          :lens="workbenchLens"
          :reconciling="activePipeline === 'feed' ? reconciling : false"
          :refreshing="dashboardRefreshing"
          :retrying-batch="activePipeline === 'feed' ? retryingBatch : false"
          :summary="dashboardSummary"
          @reconcile="handleReconcile"
          @refresh="handleRefreshAll"
          @retry-failed="handleRetryFailed"
          @set-lens="handleLensChange"
          @toggle-auto-refresh="handleToggleAutoRefresh"
        />

        <section class="pipeline-tabs">
          <Tabs :model-value="activePipeline" @update:model-value="handlePipelineChange">
            <TabsList class="pipeline-tabs__list">
              <TabsTrigger value="feed" class="pipeline-tabs__trigger">视频列表拉取</TabsTrigger>
              <TabsTrigger value="extract" class="pipeline-tabs__trigger">视频提取</TabsTrigger>
            </TabsList>
          </Tabs>
        </section>

        <section class="lane-strip" aria-hidden="true">
          <div class="lane-strip__segment">
            <span class="lane-strip__kicker">Queue</span>
            <strong class="lane-strip__title">接下来处理</strong>
            <span class="lane-strip__value">{{ currentQueuedLaneItems.length }} 项</span>
          </div>
          <div class="lane-strip__link">队首进入 →</div>
          <div class="lane-strip__segment lane-strip__segment--active">
            <span class="lane-strip__kicker">Active</span>
            <strong class="lane-strip__title">当前处理</strong>
            <span class="lane-strip__value">{{ currentActiveLaneItems.length }} 项</span>
          </div>
          <div class="lane-strip__link">完成收口 →</div>
          <div class="lane-strip__segment lane-strip__segment--done">
            <span class="lane-strip__kicker">Done</span>
            <strong class="lane-strip__title">刚处理完</strong>
            <span class="lane-strip__value">{{ currentRecentCount }} 项</span>
          </div>
        </section>

        <section class="flow-shell">
          <SyncQueueBoard
            :items="currentQueuedLaneItems"
            :loading="dashboardRefreshing"
            :error="currentQueuedError"
            @open-run="handleOpenRunFromItem"
          />

          <SyncActiveRunBoard
            :items="currentActiveLaneItems"
            :slot-count="activeSlotCount"
            :loading="dashboardRefreshing"
            :error="currentRunningError"
            :pipeline="activePipeline"
            @open-run="handleOpenRunFromItem"
          />

          <SyncRecentRunBoard
            v-if="activePipeline === 'feed'"
            :runs="recentLaneRuns"
            :loading="historyLoading"
            :error="historyError"
            :selected-run-id="selectedRunId"
            @open-run="handleSelectRun"
          />

          <SyncRecentTaskBoard
            v-else
            :items="extractionRecentItems"
            :loading="extractionLoading"
            :error="extractionRecentPreviewError"
          />
        </section>
      </div>
    </div>

    <SyncRunDetailDrawer
      :detail-error="historyDetailError"
      :detail-loading="historyDetailLoading"
      :events="historyEvents"
      :open="activePipeline === 'feed' && !!historySelectedRun"
      :run="historySelectedRun"
      :site-options="siteOptions"
      @close="handleCloseRunDrawer"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import SyncActiveRunBoard from '@/components/sync-center/SyncActiveRunBoard.vue'
import SyncControlBar from '@/components/sync-center/SyncControlBar.vue'
import SyncQueueBoard from '@/components/sync-center/SyncQueueBoard.vue'
import SyncRecentRunBoard from '@/components/sync-center/SyncRecentRunBoard.vue'
import SyncRecentTaskBoard from '@/components/sync-center/SyncRecentTaskBoard.vue'
import SyncRunDetailDrawer from '@/components/sync-center/SyncRunDetailDrawer.vue'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useExtractionCenter } from '@/composables/useExtractionCenter'
import type { SyncCenterItem } from '@/composables/useSyncCenter'
import { useSyncCenter } from '@/composables/useSyncCenter'
import { useSyncHistory } from '@/composables/useSyncHistory'
import { type SyncTimeLens, useSyncCenterWorkbench } from '@/composables/useSyncCenterWorkbench'

const {
  lens: workbenchLens,
  selectRun,
  selectedRunId,
  setLens,
} = useSyncCenterWorkbench()

const {
  autoRefresh: overviewAutoRefresh,
  filters: overviewFilters,
  filteredFailedCount,
  lastUpdatedAt: overviewLastUpdatedAt,
  loadingItems: overviewLoadingItems,
  loadingOverview,
  overview,
  pageError: overviewPageError,
  queuedPreview,
  queuedPreviewError,
  refreshAll: overviewRefreshAll,
  retryFailed,
  retryingBatch,
  reconcile,
  reconciling,
  runningPreview,
  runningPreviewError,
  siteOptions,
  total: overviewTotal,
  setPollingEnabled,
} = useSyncCenter()

const {
  closeRun: historyCloseRun,
  detailError: historyDetailError,
  detailLoading: historyDetailLoading,
  error: historyError,
  events: historyEvents,
  lastUpdatedAt: historyLastUpdatedAt,
  loadRuns: historyLoadRuns,
  loading: historyLoading,
  refreshSelectedRun: historyRefreshSelectedRun,
  runs: historyRuns,
  selectRun: historySelectRun,
  selectedRun: historySelectedRun,
  setDateRange: historySetDateRange,
} = useSyncHistory()

const {
  autoRefresh: extractionAutoRefresh,
  lastUpdatedAt: extractionLastUpdatedAt,
  loadingItems: extractionLoadingItems,
  loadingOverview: extractionLoadingOverview,
  overview: extractionOverview,
  pageError: extractionPageError,
  queuedPreview: extractionQueuedPreview,
  queuedPreviewError: extractionQueuedPreviewError,
  recentPreview: extractionRecentItems,
  recentPreviewError: extractionRecentPreviewError,
  refreshAll: extractionRefreshAll,
  runningPreview: extractionRunningPreview,
  runningPreviewError: extractionRunningPreviewError,
  setPollingEnabled: setExtractionPollingEnabled,
} = useExtractionCenter()

const activePipeline = ref<'feed' | 'extract'>('feed')

const dashboardRefreshing = computed(() => {
  if (activePipeline.value === 'extract') {
    return extractionLoadingOverview.value || extractionLoadingItems.value
  }
  return loadingOverview.value || overviewLoadingItems.value || historyLoading.value || historyDetailLoading.value
})

const extractionLoading = computed(() => {
  return extractionLoadingOverview.value || extractionLoadingItems.value
})

const toolbarLastUpdatedAt = computed(() => {
  if (activePipeline.value === 'extract') {
    return extractionLastUpdatedAt.value || ''
  }
  return overviewLastUpdatedAt.value || historyLastUpdatedAt.value || ''
})

const retryTargetCount = computed(() => {
  if (activePipeline.value === 'extract') {
    return 0
  }
  return overviewFilters.status === 'failed' ? overviewTotal.value : filteredFailedCount.value
})

const dashboardSummary = computed(() => {
  if (activePipeline.value === 'extract') {
    if (extractionPageError.value) {
      return '视频提取数据不可用'
    }
    return `提取中 ${extractionOverview.value.running_count} · 排队 ${extractionOverview.value.queued_count} · 活跃任务 ${extractionOverview.value.pending_videos}`
  }
  if (overviewPageError.value || historyError.value) {
    return '部分数据不可用'
  }
  return `运行中 ${overview.value.running_count} · 排队 ${overview.value.queued_count} · 待提取 ${overview.value.pending_videos}`
})

const currentAutoRefresh = computed(() => {
  return activePipeline.value === 'extract'
    ? extractionAutoRefresh.value
    : overviewAutoRefresh.value
})

const parseTimestamp = (value?: string | null) => {
  if (!value) return Number.POSITIVE_INFINITY
  const timestamp = new Date(value).getTime()
  return Number.isNaN(timestamp) ? Number.POSITIVE_INFINITY : timestamp
}

const activeLaneItems = computed(() => {
  return [...runningPreview.value].sort((left, right) => {
    const leftStarted = parseTimestamp(left.locked_at || left.updated_at || left.last_sync_at)
    const rightStarted = parseTimestamp(right.locked_at || right.updated_at || right.last_sync_at)
    if (leftStarted !== rightStarted) {
      return leftStarted - rightStarted
    }
    return left.subscription_id - right.subscription_id
  })
})

const extractionActiveLaneItems = computed(() => {
  return [...extractionRunningPreview.value].sort((left, right) => {
    const leftStarted = parseTimestamp(left.locked_at || left.updated_at)
    const rightStarted = parseTimestamp(right.locked_at || right.updated_at)
    if (leftStarted !== rightStarted) {
      return leftStarted - rightStarted
    }
    return left.subscription_id - right.subscription_id
  })
})

const activeSlotCount = computed(() => {
  return activePipeline.value === 'extract'
    ? Math.max(extractionOverview.value.running_count, extractionActiveLaneItems.value.length)
    : Math.max(overview.value.running_count, activeLaneItems.value.length)
})

const queuedLaneItems = computed(() => {
  return [...queuedPreview.value].sort((left, right) => {
    const leftPos = left.queue_position ?? Number.POSITIVE_INFINITY
    const rightPos = right.queue_position ?? Number.POSITIVE_INFINITY
    if (leftPos !== rightPos) {
      return leftPos - rightPos
    }

    const leftQueued = parseTimestamp(left.queued_at || left.updated_at)
    const rightQueued = parseTimestamp(right.queued_at || right.updated_at)
    if (leftQueued !== rightQueued) {
      return leftQueued - rightQueued
    }
    return left.subscription_id - right.subscription_id
  })
})

const extractionQueuedLaneItems = computed(() => {
  return [...extractionQueuedPreview.value].sort((left, right) => {
    const leftPos = left.queue_position ?? Number.POSITIVE_INFINITY
    const rightPos = right.queue_position ?? Number.POSITIVE_INFINITY
    if (leftPos !== rightPos) {
      return leftPos - rightPos
    }

    const leftQueued = parseTimestamp(left.queued_at || left.updated_at)
    const rightQueued = parseTimestamp(right.queued_at || right.updated_at)
    if (leftQueued !== rightQueued) {
      return leftQueued - rightQueued
    }
    return left.subscription_id - right.subscription_id
  })
})

const recentLaneRuns = computed(() => {
  return [...historyRuns.value]
    .filter((run) => !['created', 'queued', 'running'].includes(run.status))
    .sort((left, right) => {
      const leftFinished = parseTimestamp(left.finished_at || left.last_event_at || left.started_at)
      const rightFinished = parseTimestamp(right.finished_at || right.last_event_at || right.started_at)
      if (leftFinished !== rightFinished) {
        return rightFinished - leftFinished
      }
      return right.run_id.localeCompare(left.run_id)
    })
    .slice(0, 9)
})

const currentActiveLaneItems = computed(() => {
  return activePipeline.value === 'extract' ? extractionActiveLaneItems.value : activeLaneItems.value
})

const currentQueuedLaneItems = computed(() => {
  return activePipeline.value === 'extract' ? extractionQueuedLaneItems.value : queuedLaneItems.value
})

const currentRecentCount = computed(() => {
  return activePipeline.value === 'extract' ? extractionRecentItems.value.length : recentLaneRuns.value.length
})

const currentQueuedError = computed(() => {
  return activePipeline.value === 'extract' ? extractionQueuedPreviewError.value : queuedPreviewError.value
})

const currentRunningError = computed(() => {
  return activePipeline.value === 'extract' ? extractionRunningPreviewError.value : runningPreviewError.value
})

const getLensWindow = (lens: SyncTimeLens) => {
  const now = new Date()
  const start = new Date(now)
  if (lens === '7d') {
    start.setDate(start.getDate() - 7)
    return { dateFrom: start.toISOString(), dateTo: now.toISOString() }
  }
  if (lens === '24h') {
    start.setHours(start.getHours() - 24)
    return { dateFrom: start.toISOString(), dateTo: now.toISOString() }
  }
  start.setHours(start.getHours() - 6)
  return { dateFrom: start.toISOString(), dateTo: now.toISOString() }
}

const handleRefreshAll = async () => {
  if (activePipeline.value === 'extract') {
    await extractionRefreshAll()
    return
  }
  await Promise.all([
    overviewRefreshAll(),
    historyLoadRuns(),
    historyRefreshSelectedRun(),
  ])
}

const handleLensChange = (lens: SyncTimeLens) => {
  setLens(lens)
}

const handleToggleAutoRefresh = (value: boolean) => {
  if (activePipeline.value === 'extract') {
    extractionAutoRefresh.value = value
    return
  }
  overviewAutoRefresh.value = value
}

const handleRetryFailed = async () => {
  if (activePipeline.value === 'extract') {
    return
  }
  await retryFailed()
  await handleRefreshAll()
}

const handleReconcile = async () => {
  if (activePipeline.value === 'extract') {
    return
  }
  await reconcile()
  await handleRefreshAll()
}

const handlePipelineChange = (value: string | number) => {
  activePipeline.value = String(value) === 'extract' ? 'extract' : 'feed'
}

const handleSelectRun = (runId: string) => {
  selectRun(runId)
}

const handleCloseRunDrawer = () => {
  selectRun('')
  historyCloseRun()
}

const handleOpenRunFromItem = (item: SyncCenterItem) => {
  if (activePipeline.value === 'extract') {
    return
  }
  if (!item.run_id) {
    return
  }
  selectRun(item.run_id)
}

watch(workbenchLens, async (lens) => {
  const windowConfig = getLensWindow(lens)
  historySetDateRange(windowConfig.dateFrom, windowConfig.dateTo)
  await historyLoadRuns()
}, { immediate: true })

watch(selectedRunId, async (runId) => {
  if (!runId) {
    historyCloseRun()
    return
  }
  await historySelectRun(runId)
}, { immediate: true })

watch(activePipeline, (pipeline) => {
  if (pipeline === 'extract') {
    selectRun('')
    historyCloseRun()
  }
})

onMounted(() => {
  setPollingEnabled(true)
  setExtractionPollingEnabled(true)
})
</script>

<style scoped>
.tactical-terminal {
  background-color: #050505;
  position: relative;
  overflow: hidden;
}

.matrix-bg {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 20px 20px;
  pointer-events: none;
}

.toolbar-container {
  max-width: 1520px;
  margin: 0 auto;
  padding-left: 2rem;
  padding-right: 2rem;
  width: 100%;
}

.pipeline-tabs {
  display: flex;
  justify-content: flex-start;
}

.pipeline-tabs__list {
  height: 2.4rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.025);
  padding: 0.25rem;
  border-radius: 1rem;
}

.pipeline-tabs__trigger {
  min-width: 9.5rem;
  height: 1.8rem;
  border-radius: 0.75rem;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.48);
  text-transform: uppercase;
}

:deep(.pipeline-tabs__trigger[data-state='active']) {
  background: rgba(255, 168, 107, 0.14);
  color: rgba(255, 226, 201, 0.96);
}

.lane-strip {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex-wrap: wrap;
}

.lane-strip__segment {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  border-radius: 1rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.025);
  padding: 0.55rem 0.8rem;
}

.lane-strip__segment--active {
  border-color: rgba(255, 168, 107, 0.22);
  background: rgba(255, 168, 107, 0.08);
}

.lane-strip__segment--done {
  border-color: rgba(124, 194, 255, 0.18);
  background: rgba(124, 194, 255, 0.08);
}

.lane-strip__kicker {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.34);
}

.lane-strip__title {
  font-size: 13px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.9);
}

.lane-strip__value {
  font-size: 12px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.56);
}

.lane-strip__link {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.3);
}

.flow-shell {
  display: grid;
  gap: 1rem;
}

@media (min-width: 1280px) {
  .flow-shell {
    grid-template-columns: 0.95fr 1.1fr 0.95fr;
    align-items: start;
    grid-auto-rows: minmax(0, auto);
  }
}

@media (max-width: 900px) {
  .toolbar-container {
    padding-left: 1rem;
    padding-right: 1rem;
  }
}
</style>
