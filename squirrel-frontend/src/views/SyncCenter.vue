<template>
  <div class="sync-center-page tactical-terminal min-h-full selection:bg-primary/10">
    <div class="matrix-bg"></div>
    <div class="toolbar-container py-8 relative z-10">
      <div class="flex flex-col gap-10">
        <SyncControlBar
          :auto-refresh="overviewAutoRefresh"
          :can-retry-failed="retryTargetCount > 0"
          :last-updated-at="toolbarLastUpdatedAt"
          :lens="workbenchLens"
          :reconciling="reconciling"
          :refreshing="dashboardRefreshing"
          :retrying-batch="retryingBatch"
          :summary="dashboardSummary"
          @reconcile="handleReconcile"
          @refresh="handleRefreshAll"
          @retry-failed="handleRetryFailed"
          @set-lens="handleLensChange"
          @toggle-auto-refresh="handleToggleAutoRefresh"
        />

        <SyncAnalysisWorkspace
          :current="currentSignals"
          :recent="recentSignals"
          :run-filters="historyFilters"
          :run-page="historyPage"
          :run-page-size="historyPageSize"
          :run-total="historyTotal"
          :runs="historyRuns"
          :runs-error="historyError"
          :runs-loading="historyLoading"
          :selected-run-id="selectedRunId"
          :site-options="historySiteOptions"
          :subscription-options="historySubscriptionOptions"
          @signal-select="handleSignalSelect"
          @apply-history-filters="handleHistoryFiltersApply"
          @change-history-page="historySetPage"
          @open-run="handleSelectRun"
        />
      </div>
    </div>

    <SyncRunDetailDrawer
      :detail-error="historyDetailError"
      :detail-loading="historyDetailLoading"
      :events="historyEvents"
      :open="!!historySelectedRun"
      :run="historySelectedRun"
      :site-options="historySiteOptions"
      @close="handleCloseRunDrawer"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import SyncAnalysisWorkspace from '@/components/sync-center/SyncAnalysisWorkspace.vue'
import SyncControlBar from '@/components/sync-center/SyncControlBar.vue'
import SyncRunDetailDrawer from '@/components/sync-center/SyncRunDetailDrawer.vue'
import { type SyncSignalItem } from '@/components/sync-center/SyncSignalMatrix.vue'
import { useSyncCenter } from '@/composables/useSyncCenter'
import { type SyncHistoryFilters, useSyncHistory } from '@/composables/useSyncHistory'
import { type SyncTimeLens, useSyncCenterWorkbench } from '@/composables/useSyncCenterWorkbench'
import { useSyncTrends } from '@/composables/useSyncTrends'
import { formatDurationMs } from '@/utils/dateFormat'

const {
  lens: workbenchLens,
  resetAnalysis,
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
  refreshAll: overviewRefreshAll,
  retryFailed,
  retryingBatch,
  reconcile,
  reconciling,
  recoverySummary,
  selectStatus: overviewSelectStatus,
  total: overviewTotal,
  setPollingEnabled,
} = useSyncCenter()

const {
  closeRun: historyCloseRun,
  detailError: historyDetailError,
  detailLoading: historyDetailLoading,
  error: historyError,
  events: historyEvents,
  filters: historyFilters,
  lastUpdatedAt: historyLastUpdatedAt,
  loadRuns: historyLoadRuns,
  loading: historyLoading,
  page: historyPage,
  pageSize: historyPageSize,
  refreshSelectedRun: historyRefreshSelectedRun,
  runs: historyRuns,
  selectRun: historySelectRun,
  selectedRun: historySelectedRun,
  siteOptions: historySiteOptions,
  subscriptionOptions: historySubscriptionOptions,
  setDateRange: historySetDateRange,
  setFilters: historySetFilters,
  setPage: historySetPage,
  total: historyTotal,
} = useSyncHistory()

const {
  error: trendError,
  lastUpdatedAt: trendLastUpdatedAt,
  loadTrends,
  loading: trendLoading,
  series: trendSeries,
  setRange: trendSetRange,
} = useSyncTrends()

const dashboardRefreshing = computed(() => {
  return loadingOverview.value || overviewLoadingItems.value || historyLoading.value || historyDetailLoading.value || trendLoading.value
})

const toolbarLastUpdatedAt = computed(() => {
  return overviewLastUpdatedAt.value || historyLastUpdatedAt.value || trendLastUpdatedAt.value || ''
})

const retryTargetCount = computed(() => {
  return overviewFilters.status === 'failed' ? overviewTotal.value : filteredFailedCount.value
})

const totalTrendRuns = computed(() => trendSeries.value.reduce((sum, point) => sum + point.runs_total, 0))
const totalTrendSuccess = computed(() => trendSeries.value.reduce((sum, point) => sum + point.runs_success, 0))
const totalTrendFailed = computed(() => trendSeries.value.reduce((sum, point) => sum + point.runs_failed, 0))
const totalTrendExtracted = computed(() => trendSeries.value.reduce((sum, point) => sum + point.videos_extracted, 0))

const currentSignals = computed<SyncSignalItem[]>(() => ([
    {
    key: 'failed',
    label: '失败',
    value: overview.value.failed_count,
    tone: overview.value.failed_count ? 'error' : 'success',
  },
  {
    key: 'running',
    label: '运行中',
    value: overview.value.running_count,
    tone: overview.value.running_count ? 'info' : 'neutral',
  },
  {
    key: 'queued',
    label: '排队中',
    value: overview.value.queued_count,
    tone: overview.value.queued_count ? 'warning' : 'neutral',
  },
  {
    key: 'pending-videos',
    label: '待处理视频',
    value: overview.value.pending_videos,
    tone: overview.value.pending_videos > 0 ? 'info' : 'neutral',
  },
]))

const recentSignals = computed<SyncSignalItem[]>(() => {
  const successRate = totalTrendRuns.value ? `${Math.round((totalTrendSuccess.value / totalTrendRuns.value) * 100)}%` : '0%'

  return [
    {
      key: 'success-rate',
      label: '成功率',
      value: successRate,
      tone: totalTrendFailed.value > 0 ? 'warning' : 'success',
    },
    {
      key: 'extracted',
      label: '已提取',
      value: totalTrendExtracted.value,
      tone: totalTrendExtracted.value > 0 ? 'info' : 'neutral',
    },
  ]
})

const dashboardSummary = computed(() => {
  if (overviewPageError.value || historyError.value || trendError.value) {
    return '部分数据不可用'
  }
  return `运行稳定 · ${overview.value.running_count} 个活跃工作节点`
})

const getLensWindow = (lens: SyncTimeLens) => {
  const now = new Date()
  const start = new Date(now)
  if (lens === '7d') {
    start.setDate(start.getDate() - 7)
    return { dateFrom: start.toISOString(), dateTo: now.toISOString(), trendRange: '7d' }
  }
  if (lens === '24h') {
    start.setHours(start.getHours() - 24)
    return { dateFrom: start.toISOString(), dateTo: now.toISOString(), trendRange: '24h' }
  }
  start.setHours(start.getHours() - 6)
  return { dateFrom: start.toISOString(), dateTo: now.toISOString(), trendRange: '24h' }
}

const handleRefreshAll = async () => {
  await Promise.all([
    overviewRefreshAll(),
    historyLoadRuns(),
    historyRefreshSelectedRun(),
    loadTrends(),
  ])
}

const handleLensChange = (lens: SyncTimeLens) => {
  setLens(lens)
}

const handleToggleAutoRefresh = (value: boolean) => {
  overviewAutoRefresh.value = value
}

const handleRetryFailed = async () => {
  await retryFailed()
  await handleRefreshAll()
}

const handleReconcile = async () => {
  await reconcile()
  await handleRefreshAll()
}

const handleSelectRun = (runId: string) => {
  selectRun(runId)
}

const handleCloseRunDrawer = () => {
  selectRun('')
  historyCloseRun()
}

const handleSignalSelect = async (key: string) => {
  resetAnalysis()
  const statusMap: Record<string, any> = {
    'failed': 'failed',
    'running': 'running',
    'queued': 'queued',
  }
  const status = statusMap[key] || ''
  historySetFilters({ status })
  await historyLoadRuns()
}

const handleHistoryFiltersApply = async (payload: SyncHistoryFilters) => {
  historySetFilters(payload)
  await historyLoadRuns()
}

watch(workbenchLens, async (lens) => {
  const windowConfig = getLensWindow(lens)
  historySetDateRange(windowConfig.dateFrom, windowConfig.dateTo)
  trendSetRange(windowConfig.trendRange)
  await Promise.all([historyLoadRuns(), loadTrends()])
}, { immediate: true })

watch(selectedRunId, async (runId) => {
  if (!runId) {
    historyCloseRun()
    return
  }
  await historySelectRun(runId)
}, { immediate: true })

onMounted(() => {
  setPollingEnabled(true)
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
  max-width: 1440px;
  margin: 0 auto;
  padding-left: 2rem;
  padding-right: 2rem;
  width: 100%;
}
</style>
