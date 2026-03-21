import { reactive, ref } from 'vue'
import { getSyncTrends } from '@/api'
import { Logger } from '@/utils/logger'

export interface SyncTrendPoint {
  bucket_time: string
  site: string
  sync_mode: string
  trigger: string
  runs_total: number
  runs_success: number
  runs_failed: number
  runs_deferred: number
  videos_found: number
  videos_enqueued: number
  videos_extracted: number
  videos_skipped: number
  avg_duration_ms: number
  p95_duration_ms: number
}

export interface SyncTrendSiteBreakdown {
  site: string
  runs_total: number
  runs_success: number
  runs_failed: number
  runs_deferred: number
  videos_found: number
  videos_enqueued: number
  videos_extracted: number
}

export interface SyncTrendFilters {
  site: string
  mode: string
  trigger: string
}

interface SyncTrendResponse {
  range: string
  granularity: string
  series: SyncTrendPoint[]
  site_breakdown: SyncTrendSiteBreakdown[]
}

export function useSyncTrends() {
  const loading = ref(false)
  const error = ref('')
  const lastUpdatedAt = ref('')
  const range = ref('24h')
  const granularity = ref('hour')
  const series = ref<SyncTrendPoint[]>([])
  const siteBreakdown = ref<SyncTrendSiteBreakdown[]>([])
  const filters = reactive<SyncTrendFilters>({
    site: '',
    mode: '',
    trigger: '',
  })
  let requestSeq = 0

  const updateLastRefreshTime = () => {
    lastUpdatedAt.value = new Date().toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  const loadTrends = async () => {
    const currentSeq = ++requestSeq
    loading.value = true
    error.value = ''
    const { data, error: requestError } = await getSyncTrends<SyncTrendResponse>({
      range: range.value,
      site: filters.site || undefined,
      mode: filters.mode || undefined,
      trigger: filters.trigger || undefined,
    })
    if (currentSeq !== requestSeq) {
      return
    }
    if (requestError) {
      error.value = requestError.message || '加载趋势失败'
      Logger.error('Failed to load sync trends', requestError)
      series.value = []
      siteBreakdown.value = []
    } else if (data) {
      granularity.value = data.granularity || 'hour'
      series.value = data.series || []
      siteBreakdown.value = data.site_breakdown || []
    }
    updateLastRefreshTime()
    loading.value = false
  }

  const setRange = (value: string) => {
    if (range.value === value) {
      return false
    }
    range.value = value
    return true
  }

  const setFilters = (patch: Partial<SyncTrendFilters>) => {
    let changed = false

    Object.entries(patch).forEach(([key, value]) => {
      const nextValue = value ?? ''
      if (filters[key as keyof SyncTrendFilters] === nextValue) {
        return
      }
      filters[key as keyof SyncTrendFilters] = nextValue
      changed = true
    })

    return changed
  }

  return {
    error,
    filters,
    granularity,
    lastUpdatedAt,
    loadTrends,
    loading,
    range,
    series,
    setFilters,
    setRange,
    siteBreakdown,
  }
}
