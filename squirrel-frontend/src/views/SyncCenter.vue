<template>
  <div class="sync-center-page flex min-h-full flex-col bg-background text-foreground">
    <div class="toolbar-container pb-2 pt-4">
      <PageHeader
        title="同步中心"
        description="集中查看运行信号、失败恢复和历史批次，把刷新与排障收敛到一个工作区。"
      />
    </div>

    <div class="toolbar-container pb-4 pt-0">
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
    </div>

    <div class="content-container h-auto flex-1 min-h-0 overflow-y-auto pb-5">
      <div class="flex flex-col gap-2.5">
        <Alert
          v-if="actionNotice.message"
          :variant="actionNoticeVariant"
          :class="actionNoticeClass"
        >
          <AlertDescription>{{ actionNotice.message }}</AlertDescription>
        </Alert>

        <Alert
          v-if="loadNotice"
          class="border-amber-500/40"
        >
          <AlertDescription>{{ loadNotice }}</AlertDescription>
        </Alert>

        <SyncSignalMatrix
          :current="currentSignals"
          :recent="recentSignals"
          @select="handleSignalSelect"
        />

        <SyncAnalysisWorkspace
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
          @change-history-filter="handleHistoryFilter"
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
      @close="handleCloseRunDrawer"
    />

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import SyncAnalysisWorkspace from '@/components/sync-center/SyncAnalysisWorkspace.vue'
import SyncControlBar from '@/components/sync-center/SyncControlBar.vue'
import SyncRunDetailDrawer from '@/components/sync-center/SyncRunDetailDrawer.vue'
import SyncSignalMatrix, { type SyncSignalItem } from '@/components/sync-center/SyncSignalMatrix.vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useSyncCenter } from '@/composables/useSyncCenter'
import { type SyncHistoryFilters, useSyncHistory } from '@/composables/useSyncHistory'
import { type SyncTimeLens, useSyncCenterWorkbench } from '@/composables/useSyncCenterWorkbench'
import { useSyncTrends } from '@/composables/useSyncTrends'
import { formatDurationMs } from '@/utils/dateFormat'

type NoticeVariant = 'success' | 'warning' | 'error'

const historyFilterTimer = ref<ReturnType<typeof setTimeout> | null>(null)

const actionNotice = reactive<{
  message: string
  variant: NoticeVariant
}>({
  message: '',
  variant: 'success',
})

const actionNoticeVariant = computed(() => {
  return actionNotice.variant === 'error' ? 'destructive' : 'default'
})

const actionNoticeClass = computed(() => {
  if (actionNotice.variant === 'success') return 'border-emerald-500/40'
  if (actionNotice.variant === 'warning') return 'border-amber-500/40'
  return ''
})

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
  siteBreakdown: trendSiteBreakdown,
} = useSyncTrends()

const dashboardRefreshing = computed(() => {
  return loadingOverview.value || overviewLoadingItems.value || historyLoading.value || historyDetailLoading.value || trendLoading.value
})

const toolbarLastUpdatedAt = computed(() => {
  return overviewLastUpdatedAt.value || historyLastUpdatedAt.value || trendLastUpdatedAt.value || ''
})

const loadNotice = computed(() => {
  return [overviewPageError.value, historyError.value, trendError.value].filter(Boolean).join(' · ')
})

const retryTargetCount = computed(() => {
  return overviewFilters.status === 'failed' ? overviewTotal.value : filteredFailedCount.value
})

const totalTrendRuns = computed(() => trendSeries.value.reduce((sum, point) => sum + point.runs_total, 0))
const totalTrendSuccess = computed(() => trendSeries.value.reduce((sum, point) => sum + point.runs_success, 0))
const totalTrendFailed = computed(() => trendSeries.value.reduce((sum, point) => sum + point.runs_failed, 0))
const totalTrendExtracted = computed(() => trendSeries.value.reduce((sum, point) => sum + point.videos_extracted, 0))
const latestP95 = computed(() => {
  if (!trendSeries.value.length) {
    return 0
  }
  return trendSeries.value[trendSeries.value.length - 1]?.p95_duration_ms || 0
})
const volatileSiteCount = computed(() => {
  return trendSiteBreakdown.value.filter((item) => item.runs_failed > 0 || item.runs_deferred > 0).length
})

const failedRuns = computed(() => historyRuns.value.filter((run) => run.status === 'failed'))
const slowRuns = computed(() => [...historyRuns.value].sort((left, right) => right.duration_ms - left.duration_ms))

const currentSignals = computed<SyncSignalItem[]>(() => ([
  {
    key: 'running',
    label: '运行中',
    value: overview.value.running_count,
    tone: overview.value.running_count ? 'info' : 'neutral',
    delta: `待处理 ${overview.value.pending_videos}`,
  },
  {
    key: 'queued',
    label: '排队中',
    value: overview.value.queued_count,
    tone: overview.value.queued_count ? 'warning' : 'neutral',
    delta: `队列消息 ${overview.value.queue_messages}`,
  },
  {
    key: 'failed',
    label: '失败待处理',
    value: overview.value.failed_count,
    tone: overview.value.failed_count ? 'error' : 'success',
    delta: `候选 ${retryTargetCount.value}`,
  },
  {
    key: 'deferred',
    label: '延后执行',
    value: overview.value.deferred_count,
    tone: overview.value.deferred_count ? 'warning' : 'neutral',
    delta: `即将执行 ${overview.value.due_soon_count}`,
  },
  {
    key: 'queue-depth',
    label: '队列深度',
    value: overview.value.queue_depth,
    tone: overview.value.queue_depth > 0 ? 'warning' : 'neutral',
    delta: `消息 ${overview.value.queue_messages}`,
  },
  {
    key: 'pending-videos',
    label: '待处理视频',
    value: overview.value.pending_videos,
    tone: overview.value.pending_videos > 0 ? 'info' : 'neutral',
    delta: `运行中 ${overview.value.running_count}`,
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
      delta: `运行 ${totalTrendRuns.value}`,
    },
    {
      key: 'failed-runs',
      label: '失败运行',
      value: totalTrendFailed.value,
      tone: totalTrendFailed.value > 0 ? 'error' : 'success',
      delta: `批次 ${failedRuns.value.length}`,
    },
    {
      key: 'latest-p95',
      label: '最新 P95',
      value: formatDurationMs(latestP95.value),
      tone: latestP95.value > 0 ? 'warning' : 'neutral',
      delta: `最慢 ${formatDurationMs(slowRuns.value[0]?.duration_ms || 0)}`,
    },
    {
      key: 'recovered',
      label: '恢复次数',
      value: recoverySummary.value.total_recovered || 0,
      tone: recoverySummary.value.total_recovered ? 'warning' : 'neutral',
      delta: recoverySummary.value.last_reconcile_at || '未执行',
    },
    {
      key: 'volatile-sites',
      label: '波动站点',
      value: volatileSiteCount.value,
      tone: volatileSiteCount.value > 0 ? 'warning' : 'success',
      delta: `覆盖 ${trendSiteBreakdown.value.length}`,
    },
    {
      key: 'extracted',
      label: '提取量',
      value: totalTrendExtracted.value,
      tone: totalTrendExtracted.value > 0 ? 'info' : 'neutral',
      delta: `当前 ${workbenchLens.value}`,
    },
  ]
})

const dashboardSummary = computed(() => {
  if (overviewPageError.value || historyError.value || trendError.value) {
    return '存在部分数据不可用'
  }

  if (overview.value.failed_count > 0) {
    return `${overview.value.failed_count} 个失败待处理 · ${overview.value.running_count} 个运行中`
  }

  if (volatileSiteCount.value > 0) {
    return `当前稳定，但有 ${volatileSiteCount.value} 个站点出现波动`
  }

  if (overview.value.queued_count > 0) {
    return `${overview.value.queued_count} 个排队中 · P95 ${formatDurationMs(latestP95.value)}`
  }

  return `当前稳定 · ${overview.value.running_count} 个运行中 · 成功率 ${recentSignals.value[0]?.value || '0%'}`
})

const getLensWindow = (lens: SyncTimeLens) => {
  const now = new Date()
  const start = new Date(now)

  if (lens === '7d') {
    start.setDate(start.getDate() - 7)
    return {
      dateFrom: start.toISOString(),
      dateTo: now.toISOString(),
      trendRange: '7d',
    }
  }

  if (lens === '24h') {
    start.setHours(start.getHours() - 24)
    return {
      dateFrom: start.toISOString(),
      dateTo: now.toISOString(),
      trendRange: '24h',
    }
  }

  start.setHours(start.getHours() - 6)
  return {
    dateFrom: start.toISOString(),
    dateTo: now.toISOString(),
    trendRange: '24h',
  }
}

const syncHistoryFilters = async (patch: Partial<SyncHistoryFilters>) => {
  if (!historySetFilters(patch)) {
    return
  }
  await historyLoadRuns()
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
  const { data, error } = await retryFailed()
  if (error) {
    actionNotice.message = error.message || '批量重试失败'
    actionNotice.variant = 'error'
    return
  }

  if (data) {
    actionNotice.message = `已处理 ${data.total} 项，入队 ${data.queued} 项，执行中 ${data.in_progress} 项，失败 ${data.failed} 项`
    actionNotice.variant = data.failed > 0 ? 'warning' : 'success'
  }
}

const handleReconcile = async () => {
  const { data, error } = await reconcile()
  if (error) {
    actionNotice.message = error.message || '状态对账失败'
    actionNotice.variant = 'error'
    return
  }

  if (data) {
    actionNotice.message = `对账完成：queued 恢复 ${data.queuedRecovered}，running 恢复 ${data.runningRecovered}`
    actionNotice.variant = data.queuedRecovered || data.runningRecovered ? 'warning' : 'success'
  }
}

const handleSelectRun = (runId: string) => {
  selectRun(runId)
}

const handleCloseRunDrawer = () => {
  selectRun('')
  historyCloseRun()
}

const handleFocusFailedRuns = async (runId = '') => {
  await Promise.all([
    syncHistoryFilters({ status: 'failed' }),
    overviewSelectStatus('failed'),
  ])

  if (runId) {
    handleSelectRun(runId)
  }
}

const applyHistoryStatusFilter = async (status: SyncHistoryFilters['status']) => {
  await syncHistoryFilters({ status })
}

const handleSignalSelect = async (key: string) => {
  if (key === 'failed' || key === 'failed-runs' || key === 'success-rate') {
    await handleFocusFailedRuns()
    return
  }

  if (key === 'running') {
    resetAnalysis()
    await Promise.all([
      applyHistoryStatusFilter('running'),
      overviewSelectStatus('running'),
    ])
    return
  }

  if (key === 'queued' || key === 'queue-depth') {
    resetAnalysis()
    await Promise.all([
      applyHistoryStatusFilter('queued'),
      overviewSelectStatus('queued'),
    ])
    return
  }

  if (key === 'deferred') {
    resetAnalysis()
    await Promise.all([
      applyHistoryStatusFilter('deferred'),
      overviewSelectStatus('scheduled'),
    ])
    return
  }

  if (key === 'pending-videos') {
    resetAnalysis()
    await Promise.all([
      applyHistoryStatusFilter('running'),
      overviewSelectStatus('recent'),
    ])
    return
  }

  resetAnalysis()
  await Promise.all([
    applyHistoryStatusFilter(''),
    overviewSelectStatus('recent'),
  ])
}

const handleHistoryFilter = (payload: { key: string; value: string }) => {
  historySetFilters({
    [payload.key]: payload.value,
  } as Partial<SyncHistoryFilters>)

  if (historyFilterTimer.value) {
    clearTimeout(historyFilterTimer.value)
  }

  historyFilterTimer.value = setTimeout(async () => {
    await historyLoadRuns()
  }, 250)
}

watch(workbenchLens, async (lens) => {
  const windowConfig = getLensWindow(lens)
  const historyChanged = historySetDateRange(windowConfig.dateFrom, windowConfig.dateTo)
  const trendChanged = trendSetRange(windowConfig.trendRange)

  await Promise.all([
    historyChanged || !historyRuns.value.length ? historyLoadRuns() : Promise.resolve(),
    trendChanged || !trendSeries.value.length ? loadTrends() : Promise.resolve(),
  ])
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
