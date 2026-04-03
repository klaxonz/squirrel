import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import {
  getFeedDashboardSnapshot,
  getSupportedSites,
  getSyncCenterItems,
  getSyncCenterOverview,
  getSyncRecoverySummary,
  reconcileSyncCenter,
  retryFailedSyncItems,
  triggerRefresh,
} from '@/api'
import type { SyncRunItem } from '@/composables/useSyncHistory'
import { Logger } from '@/utils/logger'

export type SyncCenterStatusFilter = 'failed' | 'running' | 'queued' | 'scheduled' | 'recent'

export interface SyncCenterOverview {
  running_count: number
  awaiting_extract_count: number
  queued_count: number
  failed_count: number
  due_soon_count: number
  deferred_count: number
  pending_videos: number
  queue_depth: number
  queue_messages: number
}

export interface SyncCenterItem {
  run_id: string | null
  subscription_id: number
  subscription_name: string
  subscription_avatar: string | null
  site: string | null
  sync_mode: string
  sync_status: string
  display_status: string
  current_phase: string | null
  failure_count: number
  last_error: string | null
  last_error_summary: string | null
  last_sync_at: string
  last_success_at: string
  next_sync_at: string
  queued_at: string
  locked_at: string
  updated_at: string
  pending_video_count: number
  feed_completed: boolean
  has_more_pages: boolean
  queue_position: number | null
  videos_found: number
  videos_enqueued: number
  videos_extracted: number
  videos_skipped: number
  progress_percent: number
  progress_label: string
  is_deferred: boolean
  defer_reason: string | null
  batch_task_count: number
  queued_task_count: number
  running_task_count: number
  completed_task_count: number
  failed_task_count: number
}

interface SyncCenterListResponse {
  total: number
  page: number
  pageSize: number
  data: SyncCenterItem[]
}

interface FeedDashboardSnapshotResponse {
  overview: SyncCenterOverview
  runningPreview: SyncCenterItem[]
  queuedPreview: SyncCenterItem[]
  recentRuns: SyncRunItem[]
}

interface RetryFailedResponse {
  total: number
  queued: number
  in_progress: number
  failed: number
  skipped: number
}

interface SyncRecoverySummary {
  last_reconcile_at: string
  total_recovered: number
  by_type: Record<string, number>
  window_hours: number
}

interface SyncReconcileResponse {
  reconcileAt: string
  queuedStates: number
  queuedRecovered: number
  runningStates: number
  runningRecovered: number
}

interface SiteOption {
  value: string
  label: string
  iconUrl?: string | null
}

const POLL_INTERVAL = 15000

const createEmptyOverview = (): SyncCenterOverview => ({
  running_count: 0,
  awaiting_extract_count: 0,
  queued_count: 0,
  failed_count: 0,
  due_soon_count: 0,
  deferred_count: 0,
  pending_videos: 0,
  queue_depth: 0,
  queue_messages: 0,
})

const statusOptions: Array<{ value: SyncCenterStatusFilter; label: string }> = [
  { value: 'failed', label: '失败项' },
  { value: 'running', label: '运行中' },
  { value: 'queued', label: '排队中' },
  { value: 'scheduled', label: '即将执行' },
  { value: 'recent', label: '最近活动' },
]

export function useSyncCenter() {
  const overview = ref<SyncCenterOverview>(createEmptyOverview())
  const items = ref<SyncCenterItem[]>([])
  const runningPreview = ref<SyncCenterItem[]>([])
  const queuedPreview = ref<SyncCenterItem[]>([])
  const recentRuns = ref<SyncRunItem[]>([])
  const runningPreviewError = ref('')
  const queuedPreviewError = ref('')
  const filteredFailedCount = ref(0)
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const lastUpdatedAt = ref('')
  const overviewError = ref('')
  const itemsError = ref('')
  const loadingOverview = ref(false)
  const loadingItems = ref(false)
  const reconciling = ref(false)
  const retryingBatch = ref(false)
  const retryingItemId = ref<number | null>(null)
  const autoRefresh = ref(true)
  const pollingEnabled = ref(true)
  const selectedItem = ref<SyncCenterItem | null>(null)
  const recoverySummary = ref<SyncRecoverySummary>({
    last_reconcile_at: '',
    total_recovered: 0,
    by_type: {},
    window_hours: 24,
  })
  const filters = reactive({
    status: 'recent' as SyncCenterStatusFilter,
    site: '',
    query: '',
  })
  const recentDateRange = reactive({
    dateFrom: '',
    dateTo: '',
  })
  const siteOptions = ref<SiteOption[]>([])

  let pollTimer: ReturnType<typeof setInterval> | null = null
  let queryTimer: ReturnType<typeof setTimeout> | null = null
  let overviewRequestSeq = 0
  let itemsRequestSeq = 0
  let runningPreviewRequestSeq = 0
  let queuedPreviewRequestSeq = 0
  let failedCountRequestSeq = 0

  const pageError = computed(() => overviewError.value || itemsError.value)

  const syncSelectedItem = () => {
    if (!selectedItem.value) {
      return
    }
    const nextItem = items.value.find((item) => item.subscription_id === selectedItem.value?.subscription_id)
    if (nextItem) {
      selectedItem.value = nextItem
      return
    }
    const previewItem = [...runningPreview.value, ...queuedPreview.value].find(
      (item) => item.subscription_id === selectedItem.value?.subscription_id
    )
    selectedItem.value = previewItem || null
  }

  const updateLastRefreshTime = () => {
    lastUpdatedAt.value = new Date().toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  const buildFilterParams = (status: SyncCenterStatusFilter = filters.status, currentPage: number = page.value) => {
    return {
      status,
      site: filters.site || undefined,
      query: filters.query || undefined,
      page: currentPage,
      pageSize: pageSize.value,
    }
  }

  const loadFeedDashboardSnapshot = async () => {
    const [runningRequestSeq, queuedRequestSeq] = [
      ++runningPreviewRequestSeq,
      ++queuedPreviewRequestSeq,
    ]
    loadingOverview.value = true
    overviewError.value = ''
    const { data, error } = await getFeedDashboardSnapshot<FeedDashboardSnapshotResponse>({
      site: filters.site || undefined,
      query: filters.query || undefined,
      dateFrom: recentDateRange.dateFrom || undefined,
      dateTo: recentDateRange.dateTo || undefined,
    })
    if (
      runningRequestSeq !== runningPreviewRequestSeq
      || queuedRequestSeq !== queuedPreviewRequestSeq
    ) {
      return
    }
    if (error) {
      overviewError.value = error.message || '加载同步总览失败'
      runningPreviewError.value = error.message || '加载运行中预览失败'
      queuedPreviewError.value = error.message || '加载排队预览失败'
      overview.value = createEmptyOverview()
      runningPreview.value = []
      queuedPreview.value = []
      recentRuns.value = []
      Logger.error('Failed to load feed dashboard snapshot', error)
    } else if (data) {
      overview.value = {
        ...createEmptyOverview(),
        ...(data.overview || {}),
      }
      runningPreviewError.value = ''
      queuedPreviewError.value = ''
      runningPreview.value = data.runningPreview || []
      queuedPreview.value = data.queuedPreview || []
      recentRuns.value = data.recentRuns || []
      syncSelectedItem()
    }
    loadingOverview.value = false
  }

  const loadOverview = async () => {
    const requestSeq = ++overviewRequestSeq
    loadingOverview.value = true
    overviewError.value = ''
    const { data, error } = await getSyncCenterOverview()
    if (requestSeq !== overviewRequestSeq) {
      return
    }
    if (error) {
      overviewError.value = error.message || '加载同步总览失败'
      Logger.error('Failed to load sync center overview', error)
    } else if (data) {
      overview.value = {
        ...createEmptyOverview(),
        ...data,
      }
    }
    loadingOverview.value = false
  }

  const loadRecoverySummary = async () => {
    const { data, error } = await getSyncRecoverySummary<SyncRecoverySummary>()
    if (error) {
      Logger.error('Failed to load sync recovery summary', error)
      return
    }
    if (data) {
      recoverySummary.value = {
        last_reconcile_at: data.last_reconcile_at || '',
        total_recovered: data.total_recovered || 0,
        by_type: data.by_type || {},
        window_hours: data.window_hours || 24,
      }
    }
  }

  const loadItems = async () => {
    const requestSeq = ++itemsRequestSeq
    loadingItems.value = true
    itemsError.value = ''
    const { data, error } = await getSyncCenterItems<SyncCenterListResponse>(buildFilterParams())
    if (requestSeq !== itemsRequestSeq) {
      return
    }
    if (error) {
      itemsError.value = error.message || '加载同步列表失败'
      Logger.error('Failed to load sync center items', error)
      items.value = []
      total.value = 0
    } else if (data) {
      items.value = data.data || []
      total.value = data.total || 0
      page.value = data.page || 1
      pageSize.value = data.pageSize || pageSize.value
      syncSelectedItem()
    }
    loadingItems.value = false
  }

  const loadPreview = async (status: 'running' | 'queued') => {
    const requestSeq = status === 'running'
      ? ++runningPreviewRequestSeq
      : ++queuedPreviewRequestSeq
    const { data, error } = await getSyncCenterItems<SyncCenterListResponse>({
      status,
      site: filters.site || undefined,
      query: filters.query || undefined,
      page: 1,
      pageSize: status === 'running' ? 6 : 12,
    })
    const isStale = status === 'running'
      ? requestSeq !== runningPreviewRequestSeq
      : requestSeq !== queuedPreviewRequestSeq
    if (isStale) {
      return
    }
    if (error) {
      Logger.error(`Failed to load ${status} preview`, error)
      if (status === 'running') {
        runningPreviewError.value = error.message || '加载运行中预览失败'
        runningPreview.value = []
      } else {
        queuedPreviewError.value = error.message || '加载排队预览失败'
        queuedPreview.value = []
      }
      syncSelectedItem()
      return
    }

    const nextItems = data?.data || []
    if (status === 'running') {
      runningPreviewError.value = ''
      runningPreview.value = nextItems
    } else {
      queuedPreviewError.value = ''
      queuedPreview.value = nextItems
    }
    syncSelectedItem()
  }

  const loadFilteredFailedCount = async () => {
    const requestSeq = ++failedCountRequestSeq
    const { data, error } = await getSyncCenterItems<SyncCenterListResponse>({
      status: 'failed',
      site: filters.site || undefined,
      query: filters.query || undefined,
      page: 1,
      pageSize: 1,
    })
    if (requestSeq !== failedCountRequestSeq) {
      return
    }
    if (error) {
      Logger.error('Failed to load filtered failed count', error)
      if (filters.status === 'failed') {
        filteredFailedCount.value = total.value
      }
      return
    }
    filteredFailedCount.value = data?.total || 0
  }

  const loadSiteOptions = async () => {
    const { data, error } = await getSupportedSites()
    if (error) {
      Logger.error('Failed to load sync center site options', error)
      siteOptions.value = []
      return
    }

    const normalized = (data?.sites || []).map((site: Record<string, unknown>) => {
      const value = String(site.site_name || site.name || '').trim()
      const label = String(site.display_label || site.label || value).trim()
      const iconUrl = String(site.icon_url || '').trim() || null
      return { value, label, iconUrl }
    }).filter((option: SiteOption) => option.value)

    const deduped = normalized.filter((option: SiteOption, index: number, arr: SiteOption[]) => {
      return arr.findIndex((item) => item.value === option.value) === index
    })

    if (filters.site && !deduped.some((option: SiteOption) => option.value === filters.site)) {
      deduped.unshift({ value: filters.site, label: filters.site, iconUrl: null })
    }

    siteOptions.value = deduped
  }

  const refreshAll = async () => {
    await Promise.all([
      loadFeedDashboardSnapshot(),
      loadRecoverySummary(),
      loadItems(),
      loadFilteredFailedCount(),
    ])
    updateLastRefreshTime()
  }

  const selectStatus = async (status: SyncCenterStatusFilter) => {
    if (filters.status === status) {
      return
    }
    filters.status = status
    page.value = 1
    await loadItems()
    updateLastRefreshTime()
  }

  const setSite = async (site: string) => {
    filters.site = site
    page.value = 1
    await Promise.all([loadItems(), loadFeedDashboardSnapshot(), loadFilteredFailedCount()])
    updateLastRefreshTime()
  }

  const setQuery = (query: string) => {
    filters.query = query
    page.value = 1
    if (queryTimer) {
      clearTimeout(queryTimer)
    }
    queryTimer = setTimeout(async () => {
      await Promise.all([loadItems(), loadFeedDashboardSnapshot(), loadFilteredFailedCount()])
      updateLastRefreshTime()
    }, 300)
  }

  const setRecentDateRange = (dateFrom: string, dateTo: string) => {
    recentDateRange.dateFrom = dateFrom
    recentDateRange.dateTo = dateTo
  }

  const setPage = async (nextPage: number) => {
    if (nextPage < 1 || nextPage === page.value) {
      return
    }
    page.value = nextPage
    await loadItems()
    updateLastRefreshTime()
  }

  const openDetail = (item: SyncCenterItem) => {
    selectedItem.value = item
  }

  const closeDetail = () => {
    selectedItem.value = null
  }

  const retryItem = async (item: SyncCenterItem) => {
    retryingItemId.value = item.subscription_id
    const result = await triggerRefresh(item.subscription_id, item.sync_mode)
    if (!result.error) {
      await refreshAll()
    }
    retryingItemId.value = null
    return result
  }

  const retryFailed = async () => {
    retryingBatch.value = true
    const payload = {
      site: filters.site || null,
      query: filters.query || null,
    }
    const result = await retryFailedSyncItems<RetryFailedResponse>(payload)
    if (!result.error) {
      await refreshAll()
    }
    retryingBatch.value = false
    return result
  }

  const reconcile = async () => {
    reconciling.value = true
    const result = await reconcileSyncCenter<SyncReconcileResponse>()
    if (!result.error) {
      await refreshAll()
    }
    reconciling.value = false
    return result
  }

  const setPollingEnabled = (enabled: boolean) => {
    pollingEnabled.value = enabled
  }

  const clearPollTimer = () => {
    if (!pollTimer) {
      return
    }
    clearInterval(pollTimer)
    pollTimer = null
  }

  const startPolling = () => {
    clearPollTimer()
    if (!autoRefresh.value || !pollingEnabled.value) {
      return
    }
    pollTimer = setInterval(() => {
      refreshAll()
    }, POLL_INTERVAL)
  }

  watch([autoRefresh, pollingEnabled], () => {
    startPolling()
  })

  onMounted(async () => {
    await Promise.all([loadSiteOptions(), refreshAll()])
    startPolling()
  })

  onUnmounted(() => {
    clearPollTimer()
    if (queryTimer) {
      clearTimeout(queryTimer)
      queryTimer = null
    }
  })

  return {
    autoRefresh,
    closeDetail,
    filters,
    items,
    itemsError,
    lastUpdatedAt,
    loadingItems,
    loadingOverview,
    openDetail,
    overview,
    overviewError,
    page,
    pageError,
    pageSize,
    filteredFailedCount,
    queuedPreview,
    queuedPreviewError,
    reconcile,
    reconciling,
    recoverySummary,
    refreshAll,
    retryFailed,
    retryingBatch,
    retryingItemId,
    retryItem,
    recentRuns,
    runningPreview,
    runningPreviewError,
    setRecentDateRange,
    setPollingEnabled,
    selectStatus,
    selectedItem,
    setPage,
    setQuery,
    setSite,
    siteOptions,
    statusOptions,
    total,
  }
}
