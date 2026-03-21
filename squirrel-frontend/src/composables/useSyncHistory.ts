import { reactive, ref } from 'vue'
import { getSyncRunDetail, getSyncRunEvents, getSyncRuns } from '@/api'
import { Logger } from '@/utils/logger'

export interface SyncRunItem {
  run_id: string
  subscription_id: number
  subscription_name: string
  subscription_avatar: string | null
  site: string | null
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

interface SyncRunListResponse {
  total: number
  page: number
  pageSize: number
  data: SyncRunItem[]
}

export function useSyncHistory() {
  const loading = ref(false)
  const detailLoading = ref(false)
  const error = ref('')
  const detailError = ref('')
  const lastUpdatedAt = ref('')
  const runs = ref<SyncRunItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const selectedRun = ref<SyncRunItem | null>(null)
  const events = ref<SyncRunEvent[]>([])
  const filters = reactive({
    status: '',
    site: '',
    mode: '',
    trigger: '',
    dateFrom: '',
    dateTo: '',
  })
  let listRequestSeq = 0
  let detailRequestSeq = 0

  const updateLastRefreshTime = () => {
    lastUpdatedAt.value = new Date().toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  const loadRuns = async () => {
    const requestSeq = ++listRequestSeq
    loading.value = true
    error.value = ''
    const { data, error: requestError } = await getSyncRuns<SyncRunListResponse>({
      status: filters.status || undefined,
      site: filters.site || undefined,
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

  return {
    closeRun,
    detailError,
    detailLoading,
    error,
    events,
    filters,
    lastUpdatedAt,
    loadRuns,
    loading,
    page,
    pageSize,
    refreshSelectedRun,
    runs,
    selectRun,
    selectedRun,
    setPage,
    total,
  }
}
