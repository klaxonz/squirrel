<template>
  <AppPageShell class="sync-center-page" variant="compact" scrollable>
    <AppToolbarFrame class="toolbar-container relative z-10" variant="default">
      <div class="flex flex-col gap-4 md:gap-6">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <SyncControlBar
            :summary="dashboardSummary"
            class="border-none pb-0 mb-0"
          />

          <section class="pipeline-tabs self-start sm:self-auto">
            <AppSegmentedControl
              v-model="activePipeline"
              class="pipeline-tabs__control"
              :options="pipelineOptions"
              aria-label="同步流水线切换"
              @change="handlePipelineChange"
            />
          </section>
        </div>

        <div class="relative">
          <section class="flow-shell">
            <div class="flow-grid">
              <SyncQueueBoard
                :items="currentQueuedLaneItems"
                :loading="currentBoardInitialLoading"
                :error="currentQueuedError"
                :site-options="siteOptions"
                @open-run="handleOpenRunFromItem"
              />

              <SyncActiveRunBoard
                :items="currentActiveLaneItems"
                :slot-count="activeSlotCount"
                :loading="currentBoardInitialLoading"
                :error="currentRunningError"
                :pipeline="activePipeline"
                :carryover-count="activePipeline === 'feed' ? feedAwaitingExtractCount : 0"
                @open-run="handleOpenRunFromItem"
              />

              <SyncRecentRunBoard
                v-if="activePipeline === 'feed'"
                :runs="recentLaneRuns"
                :loading="feedInitialLoading"
                :error="currentRecentError"
                :selected-run-id="selectedRunId"
                @open-run="handleSelectRun"
              />

              <SyncRecentTaskBoard
                v-else
                :items="extractionRecentItems"
                :loading="extractionInitialLoading"
                :error="extractionRecentPreviewError"
              />
            </div>
          </section>
        </div>

      </div>
    </AppToolbarFrame>

    <SyncRunDetailDrawer
      :detail-error="historyDetailError"
      :detail-loading="historyDetailLoading"
      :events="historyEvents"
      :open="activePipeline === 'feed' && !!historySelectedRun"
      :run="historySelectedRun"
      :site-options="siteOptions"
      @close="handleCloseRunDrawer"
    />
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { getSyncCenterStreamUrl } from '@/api'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import AppSegmentedControl from '@/components/layout/AppSegmentedControl.vue'
import AppToolbarFrame from '@/components/layout/AppToolbarFrame.vue'
import SyncActiveRunBoard from '@/components/sync-center/SyncActiveRunBoard.vue'
import SyncControlBar from '@/components/sync-center/SyncControlBar.vue'
import SyncQueueBoard from '@/components/sync-center/SyncQueueBoard.vue'
import SyncRecentRunBoard from '@/components/sync-center/SyncRecentRunBoard.vue'
import SyncRecentTaskBoard from '@/components/sync-center/SyncRecentTaskBoard.vue'
import SyncRunDetailDrawer from '@/components/sync-center/SyncRunDetailDrawer.vue'
import { useExtractionCenter } from '@/composables/useExtractionCenter'
import type { SyncCenterItem } from '@/composables/useSyncCenter'
import { useSyncCenter } from '@/composables/useSyncCenter'
import type { SyncRunEvent, SyncRunItem } from '@/composables/useSyncHistory'
import { useSyncHistory } from '@/composables/useSyncHistory'
import { useUser } from '@/composables/useUser'
import { logoutAndRedirect } from '@/utils/auth'

const selectedRunId = ref('')
const { getCurrentUser } = useUser()

const {
  hasLoadedOnce: feedLoadedOnce,
  loadingItems: overviewLoadingItems,
  loadingOverview,
  overview,
  pageError: overviewPageError,
  queuedPreview,
  queuedPreviewError,
  recentRuns: feedRecentRuns,
  runningPreview,
  runningPreviewError,
  loadSiteOptions,
  siteOptions,
} = useSyncCenter({
  autoLoadSiteOptions: false,
})

const {
  closeRun: historyCloseRun,
  detailError: historyDetailError,
  detailLoading: historyDetailLoading,
  error: historyError,
  events: historyEvents,
  loading: historyLoading,
  selectedRun: historySelectedRun,
  setPollingEnabled: setHistoryPollingEnabled,
} = useSyncHistory({
  resolveDateRange: () => getDefaultHistoryWindow(),
  autoLoadOptions: false,
  autoStartPolling: false,
})

const {
  hasLoadedOnce: extractionLoadedOnce,
  loadingItems: extractionLoadingItems,
  loadingOverview: extractionLoadingOverview,
  overview: extractionOverview,
  pageError: extractionPageError,
  queuedPreview: extractionQueuedPreview,
  queuedPreviewError: extractionQueuedPreviewError,
  recentPreview: extractionRecentItems,
  recentPreviewError: extractionRecentPreviewError,
  runningPreview: extractionRunningPreview,
  runningPreviewError: extractionRunningPreviewError,
} = useExtractionCenter()

const activePipeline = ref<'feed' | 'extract'>('feed')
const pipelineOptions = [
  { value: 'feed', label: '列表拉取' },
  { value: 'extract', label: '视频提取' },
]
let dashboardStream: EventSource | null = null
let dashboardStreamAuthChecking = false

const dashboardRefreshing = computed(() => {
  if (activePipeline.value === 'extract') {
    return extractionLoadingOverview.value || extractionLoadingItems.value
  }
  return loadingOverview.value || overviewLoadingItems.value || historyLoading.value || historyDetailLoading.value
})

const extractionLoading = computed(() => {
  return extractionLoadingOverview.value || extractionLoadingItems.value
})

const feedInitialLoading = computed(() => {
  return dashboardRefreshing.value && !feedLoadedOnce.value
})

const extractionInitialLoading = computed(() => {
  return extractionLoading.value && !extractionLoadedOnce.value
})

const currentBoardInitialLoading = computed(() => {
  return activePipeline.value === 'extract' ? extractionInitialLoading.value : feedInitialLoading.value
})

const dashboardSummary = computed(() => {
  if (activePipeline.value === 'extract') {
    if (extractionPageError.value) {
      return '视频提取数据不可用'
    }
    return `提取中 ${extractionOverview.value.running_count} · 排队 ${extractionOverview.value.queued_count} · 活跃提取任务 ${extractionOverview.value.pending_videos}`
  }
  if (overviewPageError.value || historyError.value) {
    return '部分数据不可用'
  }
  return `列表拉取中 ${overview.value.running_count} · 排队 ${overview.value.queued_count} · 等待提取收口 ${overview.value.awaiting_extract_count}`
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

const feedActiveLaneItems = computed(() => {
  return activeLaneItems.value
})

const feedAwaitingExtractCount = computed(() => {
  return overview.value.awaiting_extract_count
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
  return [...feedRecentRuns.value]
    .sort((left, right) => {
      const leftFinished = parseTimestamp(left.feed_completed_at || left.finished_at || left.last_event_at || left.started_at)
      const rightFinished = parseTimestamp(right.feed_completed_at || right.finished_at || right.last_event_at || right.started_at)
      if (leftFinished !== rightFinished) {
        return rightFinished - leftFinished
      }
      return right.run_id.localeCompare(left.run_id)
    })
})

const currentRecentError = computed(() => {
  return ''
})

const currentActiveLaneItems = computed(() => {
  return activePipeline.value === 'extract' ? extractionActiveLaneItems.value : feedActiveLaneItems.value
})

const currentQueuedLaneItems = computed(() => {
  return activePipeline.value === 'extract' ? extractionQueuedLaneItems.value : queuedLaneItems.value
})

const currentQueuedError = computed(() => {
  return activePipeline.value === 'extract' ? extractionQueuedPreviewError.value : queuedPreviewError.value
})

const currentRunningError = computed(() => {
  return activePipeline.value === 'extract' ? extractionRunningPreviewError.value : runningPreviewError.value
})

const getDefaultHistoryWindow = () => {
  const end = new Date()
  const start = new Date(end)
  start.setHours(start.getHours() - 6)
  return {
    dateFrom: start.toISOString(),
    dateTo: end.toISOString(),
  }
}

const handlePipelineChange = (value: string | number) => {
  activePipeline.value = String(value) === 'extract' ? 'extract' : 'feed'
}

const handleSelectRun = (runId: string) => {
  selectedRunId.value = runId
}

const handleCloseRunDrawer = () => {
  selectedRunId.value = ''
  historyCloseRun()
}

const handleOpenRunFromItem = (item: SyncCenterItem) => {
  if (activePipeline.value === 'extract') {
    return
  }
  if (!item.run_id) {
    return
  }
  selectedRunId.value = item.run_id
}

const closeDashboardStream = () => {
  if (!dashboardStream) {
    return
  }
  dashboardStream.close()
  dashboardStream = null
}

const applyFeedSnapshot = (snapshot: {
  overview?: Record<string, unknown>
  runningPreview?: SyncCenterItem[]
  queuedPreview?: SyncCenterItem[]
  recentRuns?: SyncRunItem[]
}) => {
  overview.value = {
    ...overview.value,
    ...(snapshot.overview || {}),
  }
  runningPreview.value = snapshot.runningPreview || []
  queuedPreview.value = snapshot.queuedPreview || []
  feedRecentRuns.value = snapshot.recentRuns || []
  runningPreviewError.value = ''
  queuedPreviewError.value = ''
  overviewLoadingItems.value = false
  loadingOverview.value = false
  feedLoadedOnce.value = true
}

const applyExtractSnapshot = (snapshot: {
  overview?: Record<string, unknown>
  runningPreview?: SyncCenterItem[]
  queuedPreview?: SyncCenterItem[]
  recentPreview?: SyncCenterItem[]
}) => {
  extractionOverview.value = {
    ...extractionOverview.value,
    ...(snapshot.overview || {}),
  }
  extractionRunningPreview.value = snapshot.runningPreview || []
  extractionQueuedPreview.value = snapshot.queuedPreview || []
  extractionRecentItems.value = snapshot.recentPreview || []
  extractionRunningPreviewError.value = ''
  extractionQueuedPreviewError.value = ''
  extractionRecentPreviewError.value = ''
  extractionLoadingItems.value = false
  extractionLoadingOverview.value = false
  extractionLoadedOnce.value = true
}

const applyRunDetailSnapshot = (snapshot: {
  run?: SyncRunItem | null
  events?: SyncRunEvent[]
}) => {
  historySelectedRun.value = snapshot.run || null
  historyEvents.value = snapshot.events || []
  historyDetailError.value = ''
  historyDetailLoading.value = false
}

const verifyDashboardStreamAuth = async () => {
  if (dashboardStreamAuthChecking) {
    return
  }
  dashboardStreamAuthChecking = true
  try {
    const result = await getCurrentUser()
    if (result.error?.status === 401) {
      closeDashboardStream()
      await logoutAndRedirect()
    }
  } finally {
    dashboardStreamAuthChecking = false
  }
}

const openDashboardStream = () => {
  closeDashboardStream()
  if (!feedLoadedOnce.value) {
    overviewLoadingItems.value = true
    loadingOverview.value = true
  }
  if (!extractionLoadedOnce.value) {
    extractionLoadingItems.value = true
    extractionLoadingOverview.value = true
  }
  if (selectedRunId.value) {
    historyDetailLoading.value = true
  }
  dashboardStream = new EventSource(getSyncCenterStreamUrl(selectedRunId.value))

  dashboardStream.addEventListener('feed_snapshot', (event) => {
    const snapshot = JSON.parse((event as MessageEvent).data)
    applyFeedSnapshot(snapshot)
  })

  dashboardStream.addEventListener('extract_snapshot', (event) => {
    const snapshot = JSON.parse((event as MessageEvent).data)
    applyExtractSnapshot(snapshot)
  })

  dashboardStream.addEventListener('run_detail', (event) => {
    const snapshot = JSON.parse((event as MessageEvent).data)
    applyRunDetailSnapshot(snapshot)
  })

  dashboardStream.onerror = () => {
    void verifyDashboardStreamAuth()
  }
}

onMounted(() => {
  setHistoryPollingEnabled(false)
  void loadSiteOptions()
  openDashboardStream()
})

watch(selectedRunId, (runId) => {
  if (!runId) {
    historyCloseRun()
  }
  openDashboardStream()
})

watch(activePipeline, (pipeline) => {
  if (pipeline === 'extract') {
    selectedRunId.value = ''
    historyCloseRun()
  }
})

onBeforeUnmount(() => {
  closeDashboardStream()
})
</script>

<style scoped>
.pipeline-tabs {
  display: flex;
  justify-content: flex-start;
}

.pipeline-tabs__control {
  min-width: max-content;
}

.flow-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.5rem;
  max-height: calc(100vh - 16rem);
  overflow: hidden;
}

@media (min-width: 640px) {
  .flow-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.75rem;
    max-height: calc(100vh - 14rem);
  }
}

@media (min-width: 1024px) {
  .flow-grid {
    gap: 1rem;
    max-height: calc(100vh - 12rem);
  }
}
</style>
