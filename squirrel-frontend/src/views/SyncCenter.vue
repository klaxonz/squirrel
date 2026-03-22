<template>
  <div class="sync-center-page flex min-h-full flex-col bg-bg-primary text-text-primary">
    <div class="toolbar-container pb-4 pt-4">
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

    <div class="content-container h-auto flex-1 min-h-0 overflow-y-auto pb-6">
      <div class="flex flex-col gap-3">
        <InlineAlert
          v-if="actionNotice.message"
          :message="actionNotice.message"
          :variant="actionNotice.variant"
        />

        <InlineAlert
          v-if="loadNotice"
          :message="loadNotice"
          variant="warning"
        />

        <SyncSignalMatrix
          :current="currentSignals"
          :recent="recentSignals"
          @select="handleSignalSelect"
        />

        <SyncFocusBoard
          :active-focus="workbenchFocus"
          :failed-runs="failedFocusRows"
          :recovery="recoveryFocusRows"
          :sites="siteFocusRows"
          :slow-runs="slowFocusRows"
          @open="handleFocusBoardOpen"
        />

        <SyncAnalysisWorkspace
          :focus="workbenchFocus"
          :item-page="overviewPage"
          :item-page-size="overviewPageSize"
          :item-status="overviewFilters.status"
          :item-total="overviewTotal"
          :items="analysisItems"
          :items-loading="overviewLoadingItems"
          :recovery-summary="recoverySummary"
          :retrying-id="retryingItemId"
          :run-filters="historyFilters"
          :run-page="historyPage"
          :run-page-size="historyPageSize"
          :run-total="historyTotal"
          :runs="historyRuns"
          :runs-error="historyError"
          :runs-loading="historyLoading"
          :selected-item="selectedAnalysisItem"
          :selected-run="historySelectedRun"
          :selected-run-id="selectedRunId"
          :selected-subscription-id="selectedSubscriptionId"
          :site="workbenchSite"
          :site-breakdown="trendSiteBreakdown"
          :trend-error="trendError"
          :trend-filters="trendFilters"
          :trend-loading="trendLoading"
          :trend-range="trendRange"
          :trend-series="trendSeries"
          @change-history-filter="handleHistoryFilter"
          @change-history-page="historySetPage"
          @change-item-page="overviewSetPage"
          @change-item-status="handleOverviewStatusChange"
          @change-trend-filter="handleTrendFilter"
          @change-trend-range="handleTrendRange"
          @focus-site="handleFocusSite"
          @open-item="handleOpenItem"
          @open-recovery="handleFocusRecovery"
          @open-run="handleSelectRun"
          @retry-item="handleRetryItem"
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

    <SyncDetailDrawer
      :item="overviewSelectedItem"
      :open="!!overviewSelectedItem"
      :retrying="retryingItemId === overviewSelectedItem?.subscription_id"
      @close="handleCloseItemDrawer"
      @retry="handleRetrySelected"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { InlineAlert } from '@/components/common'
import SyncAnalysisWorkspace from '@/components/sync-center/SyncAnalysisWorkspace.vue'
import SyncControlBar from '@/components/sync-center/SyncControlBar.vue'
import SyncDetailDrawer from '@/components/sync-center/SyncDetailDrawer.vue'
import SyncFocusBoard, { type SyncFocusRow } from '@/components/sync-center/SyncFocusBoard.vue'
import SyncRunDetailDrawer from '@/components/sync-center/SyncRunDetailDrawer.vue'
import SyncSignalMatrix, { type SyncSignalItem } from '@/components/sync-center/SyncSignalMatrix.vue'
import type { SyncCenterItem, SyncCenterStatusFilter } from '@/composables/useSyncCenter'
import { useSyncCenter } from '@/composables/useSyncCenter'
import { type SyncHistoryFilters, type SyncRunItem, useSyncHistory } from '@/composables/useSyncHistory'
import { type SyncFocusKind, type SyncTimeLens, useSyncCenterWorkbench } from '@/composables/useSyncCenterWorkbench'
import { type SyncTrendFilters, useSyncTrends } from '@/composables/useSyncTrends'
import { formatDurationMs } from '@/utils/dateFormat'

type NoticeVariant = 'success' | 'warning' | 'error'

const historyFilterTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const trendFilterTimer = ref<ReturnType<typeof setTimeout> | null>(null)

const actionNotice = reactive<{
  message: string
  variant: NoticeVariant
}>({
  message: '',
  variant: 'success',
})

const {
  analysisVisible,
  focus: workbenchFocus,
  lens: workbenchLens,
  resetAnalysis,
  selectRun,
  selectSubscription,
  selectedRunId,
  selectedSubscriptionId,
  setFocus,
  setLens,
  setSite,
  site: workbenchSite,
} = useSyncCenterWorkbench()

const {
  autoRefresh: overviewAutoRefresh,
  closeDetail: overviewCloseDetail,
  filters: overviewFilters,
  filteredFailedCount,
  items: overviewItems,
  lastUpdatedAt: overviewLastUpdatedAt,
  loadingItems: overviewLoadingItems,
  loadingOverview,
  openDetail: overviewOpenDetail,
  overview,
  page: overviewPage,
  pageError: overviewPageError,
  pageSize: overviewPageSize,
  queuedPreview,
  refreshAll: overviewRefreshAll,
  retryFailed,
  retryingBatch,
  retryingItemId,
  retryItem,
  runningPreview,
  reconcile,
  reconciling,
  recoverySummary,
  selectStatus: overviewSelectStatus,
  selectedItem: overviewSelectedItem,
  setPage: overviewSetPage,
  setPollingEnabled,
  setSite: overviewSetSite,
  total: overviewTotal,
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
  setDateRange: historySetDateRange,
  setFilters: historySetFilters,
  setPage: historySetPage,
  total: historyTotal,
} = useSyncHistory()

const {
  error: trendError,
  filters: trendFilters,
  lastUpdatedAt: trendLastUpdatedAt,
  loadTrends,
  loading: trendLoading,
  range: trendRange,
  series: trendSeries,
  setFilters: trendSetFilters,
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

const allKnownItems = computed(() => {
  const seen = new Map<number, SyncCenterItem>()

  ;[...runningPreview.value, ...queuedPreview.value, ...overviewItems.value].forEach((item) => {
    if (!seen.has(item.subscription_id)) {
      seen.set(item.subscription_id, item)
    }
  })

  return Array.from(seen.values())
})

const selectedAnalysisItem = computed(() => {
  if (selectedSubscriptionId.value == null) {
    return overviewSelectedItem.value
  }

  return allKnownItems.value.find((item) => item.subscription_id === selectedSubscriptionId.value) || overviewSelectedItem.value || null
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

const analysisItems = computed(() => {
  if (workbenchFocus.value === 'site' && workbenchSite.value) {
    return overviewItems.value.filter((item) => item.site === workbenchSite.value)
  }

  return overviewItems.value
})

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
    delta: `预览 ${allKnownItems.value.length}`,
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

const siteFocusRows = computed<SyncFocusRow[]>(() => {
  return trendSiteBreakdown.value
    .filter((item) => item.runs_failed > 0 || item.runs_deferred > 0)
    .sort((left, right) => right.runs_failed - left.runs_failed || right.runs_total - left.runs_total)
    .slice(0, 6)
    .map((item) => ({
      id: item.site,
      title: item.site,
      meta: `运行 ${item.runs_total} · 成功 ${item.runs_success}`,
      value: item.runs_failed || item.runs_deferred,
      tone: item.runs_failed > 0 ? 'error' : 'warning',
    }))
})

const failedFocusRows = computed<SyncFocusRow[]>(() => {
  return failedRuns.value.slice(0, 6).map((run) => ({
    id: run.run_id,
    title: run.subscription_name,
    meta: `${run.site || 'unknown'} ${run.last_event_at || run.finished_at || '—'}`,
    value: formatDurationMs(run.duration_ms),
    tone: 'error',
    avatar: run.subscription_avatar,
    subscriptionId: run.subscription_id,
  }))
})

const slowFocusRows = computed<SyncFocusRow[]>(() => {
  return slowRuns.value.slice(0, 6).map((run) => ({
    id: run.run_id,
    title: run.subscription_name,
    meta: `${run.site || 'unknown'} · ${run.status}`,
    value: formatDurationMs(run.duration_ms),
    tone: run.status === 'failed' ? 'error' : 'warning',
    avatar: run.subscription_avatar,
    subscriptionId: run.subscription_id,
  }))
})

const recoveryFocusRows = computed<SyncFocusRow[]>(() => ([
  {
    id: 'total',
    title: '恢复总数',
    meta: recoverySummary.value.last_reconcile_at || '未执行对账',
    value: recoverySummary.value.total_recovered || 0,
    tone: recoverySummary.value.total_recovered ? 'warning' : 'neutral',
  },
  {
    id: 'queued',
    title: 'queued 恢复',
    meta: '缺失消息或残留状态',
    value: recoverySummary.value.by_type?.stale_queued_recovered || 0,
    tone: 'warning',
  },
  {
    id: 'running',
    title: 'running 恢复',
    meta: '超时或锁残留',
    value: recoverySummary.value.by_type?.stale_running_recovered || 0,
    tone: 'info',
  },
]))

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

const syncTrendFilters = async (patch: Partial<SyncTrendFilters>) => {
  if (!trendSetFilters(patch)) {
    return
  }
  await loadTrends()
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

const handleRetryItem = async (item: SyncCenterItem) => {
  selectSubscription(item.subscription_id)
  const result = await retryItem(item)
  if (result.error) {
    actionNotice.message = result.error.message || '重试失败'
    actionNotice.variant = 'error'
    return
  }
  actionNotice.message = `已提交重试：${item.subscription_name}`
  actionNotice.variant = 'success'
}

const handleRetrySelected = async () => {
  if (!overviewSelectedItem.value) {
    return
  }

  const result = await retryItem(overviewSelectedItem.value)
  if (result.error) {
    actionNotice.message = result.error.message || '重试失败'
    actionNotice.variant = 'error'
    return
  }

  actionNotice.message = `已提交重试：${overviewSelectedItem.value.subscription_name}`
  actionNotice.variant = 'success'
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

const handleOverviewStatusChange = async (status: SyncCenterStatusFilter) => {
  await overviewSelectStatus(status)
}

const handleSelectRun = (runId: string) => {
  selectRun(runId)
}

const handleCloseRunDrawer = () => {
  selectRun('')
  historyCloseRun()
}

const handleOpenItem = (item: SyncCenterItem) => {
  selectSubscription(item.subscription_id)
  overviewOpenDetail(item)
}

const handleCloseItemDrawer = () => {
  selectSubscription(null)
  overviewCloseDetail()
}

const handleFocusSite = async (site: string) => {
  setFocus('site')
  setSite(site)
  await overviewSelectStatus('recent')
}

const handleFocusFailedRuns = async (runId = '') => {
  setFocus('failed-runs')
  await Promise.all([
    syncHistoryFilters({ status: 'failed' }),
    overviewSelectStatus('failed'),
  ])

  if (runId) {
    handleSelectRun(runId)
  }
}

const handleFocusSlowRuns = async (runId = '') => {
  setFocus('slow-runs')
  await Promise.all([
    syncHistoryFilters({ status: '' }),
    overviewSelectStatus('recent'),
  ])

  if (runId) {
    handleSelectRun(runId)
  }
}

const handleFocusRecovery = async () => {
  setFocus('recovery')
  await Promise.all([
    syncHistoryFilters({ status: '' }),
    overviewSelectStatus('queued'),
  ])
}

const handleFocusBoardOpen = async (payload: { section: Exclude<SyncFocusKind, 'overview'>; id?: string }) => {
  switch (payload.section) {
    case 'site':
      await handleFocusSite(payload.id || siteFocusRows.value[0]?.id || workbenchSite.value)
      return
    case 'failed-runs':
      await handleFocusFailedRuns(payload.id || '')
      return
    case 'slow-runs':
      await handleFocusSlowRuns(payload.id || '')
      return
    case 'recovery':
      await handleFocusRecovery()
      return
  }
}

const handleSignalSelect = async (key: string) => {
  if (key === 'failed' || key === 'failed-runs' || key === 'success-rate') {
    await handleFocusFailedRuns()
    return
  }

  if (key === 'latest-p95' || key === 'volatile-sites') {
    await handleFocusSlowRuns()
    return
  }

  if (key === 'recovered') {
    await handleFocusRecovery()
    return
  }

  if (key === 'running') {
    resetAnalysis()
    await overviewSelectStatus('running')
    return
  }

  if (key === 'queued' || key === 'queue-depth') {
    resetAnalysis()
    await overviewSelectStatus('queued')
    return
  }

  if (key === 'deferred') {
    resetAnalysis()
    await overviewSelectStatus('scheduled')
    return
  }

  resetAnalysis()
  await overviewSelectStatus('recent')
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

const handleTrendFilter = (payload: { key: string; value: string }) => {
  trendSetFilters({
    [payload.key]: payload.value,
  } as Partial<SyncTrendFilters>)

  if (trendFilterTimer.value) {
    clearTimeout(trendFilterTimer.value)
  }

  trendFilterTimer.value = setTimeout(async () => {
    await loadTrends()
  }, 250)
}

const handleTrendRange = async (value: string) => {
  if (!trendSetRange(value)) {
    return
  }
  await loadTrends()
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

watch(workbenchSite, async (site) => {
  await Promise.all([
    overviewFilters.site !== site ? overviewSetSite(site) : Promise.resolve(),
    historySetFilters({ site }) ? historyLoadRuns() : Promise.resolve(),
    trendSetFilters({ site }) ? loadTrends() : Promise.resolve(),
  ])
}, { immediate: true })

watch(selectedRunId, async (runId) => {
  if (!runId) {
    historyCloseRun()
    return
  }
  await historySelectRun(runId)
}, { immediate: true })

watch([selectedSubscriptionId, allKnownItems], ([subscriptionId, items]) => {
  if (subscriptionId == null) {
    overviewCloseDetail()
    return
  }

  const nextItem = items.find((item) => item.subscription_id === subscriptionId)
  if (nextItem) {
    overviewOpenDetail(nextItem)
    return
  }

  overviewCloseDetail()
}, { immediate: true })

onMounted(() => {
  setPollingEnabled(true)
  if (!analysisVisible.value) {
    void handleFocusFailedRuns()
  }
})
</script>
