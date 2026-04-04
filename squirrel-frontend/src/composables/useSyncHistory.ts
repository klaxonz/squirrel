import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { getSubscriptionOptions, getSupportedSites, getSyncRunDetail, getSyncRunEvents, getSyncRuns } from '@/api'
import { Logger } from '@/utils/logger'

export interface SyncRunItem {
  run_id: string
  subscription_id: number
  subscription_name: string
  subscription_avatar: string | null
  site: string | null
  site_icon_url: string | null
  sync_mode: string
  trigger: string | null
  status: string
  current_phase: string | null
  request_id: string | null
  trace_id: string | null
  queued_at: string
  started_at: string
  finished_at: string
  duration_ms: number
  failure_count: number
  error_type: string | null
  error_message: string | null
  videos_found: number
  videos_enqueued: number
  videos_extracted: number
  videos_skipped: number
  source_video_count?: number | null
  pending_video_count: number
  feed_completed: boolean
  feed_completed_at: string
  progress_percent: number
  progress_label: string
  last_event_at: string
}

export interface SyncRunEvent {
  id: number
  stream_id: string
  subscription_id: number
  sync_state_id: number | null
  site: string | null
  sync_mode: string
  trigger: string | null
  request_id: string | null
  trace_id: string | null
  event_type: string
  event_phase: string | null
  event_status: string | null
  seq_no: number
  message: string | null
  payload: Record<string, unknown>
  occurred_at: string
  projected_at: string
}

export interface SyncHistoryFilters {
  status: string
  site: string
  subscriptionId: string
  mode: string
  trigger: string
  dateFrom: string
  dateTo: string
}

interface SyncRunListResponse {
  total: number
  page: number
  pageSize: number
  data: SyncRunItem[]
}

interface SiteOption {
  value: string
  label: string
  iconUrl?: string | null
}

interface SubscriptionOption {
  value: string
  label: string
  avatar: string | null
}

interface SubscriptionOptionListResponse {
  data: Array<{
    subscription_id: number
    subscription_name: string
    subscription_avatar: string | null
  }>
}

interface UseSyncHistoryOptions {
  resolveDateRange?: () => { dateFrom: string; dateTo: string } | null
  autoLoadOptions?: boolean
  autoStartPolling?: boolean
}

const POLL_INTERVAL = 15000

export function useSyncHistory(options: UseSyncHistoryOptions = {}) {
  const {
    autoLoadOptions = true,
    autoStartPolling = true,
  } = options
  const loading = ref(false)
  const detailLoading = ref(false)
  const error = ref('')
  const detailError = ref('')
  const lastUpdatedAt = ref('')
  const pollingEnabled = ref(true)
  const runs = ref<SyncRunItem[]>([])
  const siteOptions = ref<SiteOption[]>([])
  const subscriptionOptions = ref<SubscriptionOption[]>([{ value: '', label: '全部频道', avatar: null }])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const selectedRun = ref<SyncRunItem | null>(null)
  const events = ref<SyncRunEvent[]>([])
  const filters = reactive<SyncHistoryFilters>({
    status: '',
    site: '',
    subscriptionId: '',
    mode: '',
    trigger: '',
    dateFrom: '',
    dateTo: '',
  })
  let listRequestSeq = 0
  let detailRequestSeq = 0
  let pollTimer: ReturnType<typeof setInterval> | null = null

  const loadSubscriptionOptions = async () => {
    const { data, error: requestError } = await getSubscriptionOptions<SubscriptionOptionListResponse>()
    if (requestError) {
      Logger.error('Failed to load sync history subscription options', requestError)
      subscriptionOptions.value = [{ value: '', label: '全部频道', avatar: null }]
      return
    }

    const normalized = (data?.data || []).map((item) => ({
      value: String(item.subscription_id),
      label: item.subscription_name,
      avatar: item.subscription_avatar || null,
    })).filter((option: SubscriptionOption) => option.value && option.label)

    const deduped = normalized.filter((option: SubscriptionOption, index: number, arr: SubscriptionOption[]) => {
      return arr.findIndex((item: SubscriptionOption) => item.value === option.value) === index
    })

    if (filters.subscriptionId && !deduped.some((option: SubscriptionOption) => option.value === filters.subscriptionId)) {
      deduped.unshift({ value: filters.subscriptionId, label: filters.subscriptionId, avatar: null })
    }

    subscriptionOptions.value = [
      { value: '', label: '全部频道', avatar: null },
      ...deduped,
    ]
  }

  const loadSiteOptions = async () => {
    const { data, error: requestError } = await getSupportedSites()
    if (requestError) {
      Logger.error('Failed to load sync history site options', requestError)
      siteOptions.value = [{ value: '', label: '全部站点', iconUrl: null }]
      return
    }

    const normalized = (data?.sites || []).map((site: Record<string, unknown> | string) => {
      if (typeof site === 'string') {
        return {
          value: site.trim(),
          label: site.trim(),
          iconUrl: null,
        }
      }
      const value = String(site.site_name || site.name || '').trim()
      const label = String(site.display_label || site.label || value).trim()
      const iconUrl = String(site.icon_url || '').trim() || null
      return { value, label, iconUrl }
    }).filter((option: SiteOption) => option.value)

    const deduped = normalized.filter((option: SiteOption, index: number, arr: SiteOption[]) => {
      return arr.findIndex((item: SiteOption) => item.value === option.value) === index
    })

    if (filters.site && !deduped.some((option: SiteOption) => option.value === filters.site)) {
      deduped.unshift({ value: filters.site, label: filters.site, iconUrl: null })
    }

    siteOptions.value = [
      { value: '', label: '全部站点', iconUrl: null },
      ...deduped,
    ]
  }

  const updateLastRefreshTime = () => {
    lastUpdatedAt.value = new Date().toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  const loadRuns = async () => {
    const resolvedDateRange = options.resolveDateRange?.()
    if (resolvedDateRange) {
      setDateRange(resolvedDateRange.dateFrom, resolvedDateRange.dateTo)
    }

    const requestSeq = ++listRequestSeq
    loading.value = true
    error.value = ''
    const { data, error: requestError } = await getSyncRuns<SyncRunListResponse>({
      status: filters.status || undefined,
      site: filters.site || undefined,
      subscriptionId: filters.subscriptionId || undefined,
      mode: filters.mode || undefined,
      trigger: filters.trigger || undefined,
      dateFrom: filters.dateFrom || undefined,
      dateTo: filters.dateTo || undefined,
      page: page.value,
      pageSize: pageSize.value,
    })
    if (requestSeq !== listRequestSeq) {
      return
    }
    if (requestError) {
      error.value = requestError.message || '加载运行历史失败'
      Logger.error('Failed to load sync runs', requestError)
      runs.value = []
      total.value = 0
    } else if (data) {
      runs.value = data.data || []
      total.value = data.total || 0
      page.value = data.page || 1
      pageSize.value = data.pageSize || pageSize.value
    }
    updateLastRefreshTime()
    loading.value = false
  }

  const selectRun = async (runId: string) => {
    const requestSeq = ++detailRequestSeq
    detailLoading.value = true
    detailError.value = ''
    const [detailResult, eventsResult] = await Promise.all([
      getSyncRunDetail<SyncRunItem>(runId),
      getSyncRunEvents<SyncRunEvent[]>(runId),
    ])
    if (requestSeq !== detailRequestSeq) {
      return
    }
    if (detailResult.error) {
      detailError.value = detailResult.error.message || '加载运行详情失败'
      Logger.error('Failed to load sync run detail', detailResult.error)
      selectedRun.value = null
      events.value = []
      detailLoading.value = false
      return
    }
    selectedRun.value = detailResult.data || null
    if (eventsResult.error) {
      detailError.value = eventsResult.error.message || '加载运行事件失败'
      Logger.error('Failed to load sync run events', eventsResult.error)
      events.value = []
    } else {
      events.value = eventsResult.data || []
    }
    updateLastRefreshTime()
    detailLoading.value = false
  }

  const refreshSelectedRun = async () => {
    if (!selectedRun.value?.run_id) {
      return
    }
    await selectRun(selectedRun.value.run_id)
  }

  const refreshAll = async () => {
    await Promise.all([
      loadRuns(),
      refreshSelectedRun(),
    ])
  }

  const closeRun = () => {
    detailRequestSeq += 1
    selectedRun.value = null
    events.value = []
    detailError.value = ''
    detailLoading.value = false
  }

  const setPage = async (nextPage: number) => {
    if (nextPage < 1 || nextPage === page.value) {
      return
    }
    page.value = nextPage
    await loadRuns()
  }

  const setFilters = (patch: Partial<SyncHistoryFilters>) => {
    let changed = false

    Object.entries(patch).forEach(([key, value]) => {
      const nextValue = value ?? ''
      if (filters[key as keyof SyncHistoryFilters] === nextValue) {
        return
      }
      filters[key as keyof SyncHistoryFilters] = nextValue
      changed = true
    })

    if (changed) {
      page.value = 1
    }

    return changed
  }

  const setDateRange = (dateFrom: string, dateTo: string) => {
    return setFilters({
      dateFrom,
      dateTo,
    })
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
    if (!pollingEnabled.value) {
      return
    }
    pollTimer = setInterval(() => {
      refreshAll()
    }, POLL_INTERVAL)
  }

  watch(pollingEnabled, () => {
    startPolling()
  })

  onMounted(() => {
    if (autoLoadOptions) {
      loadSiteOptions()
      loadSubscriptionOptions()
    }
    if (autoStartPolling) {
      startPolling()
    }
  })

  onUnmounted(() => {
    clearPollTimer()
  })

  return {
    closeRun,
    detailError,
    detailLoading,
    error,
    events,
    filters,
    lastUpdatedAt,
    loadRuns,
    loadSiteOptions,
    loadSubscriptionOptions,
    loading,
    page,
    pageSize,
    refreshAll,
    refreshSelectedRun,
    runs,
    selectRun,
    selectedRun,
    setPollingEnabled,
    siteOptions,
    subscriptionOptions,
    setDateRange,
    setFilters,
    setPage,
    total,
  }
}
