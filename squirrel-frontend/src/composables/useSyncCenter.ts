import { computed, onMounted, ref } from 'vue'
import { getSupportedSites } from '@/api'
import type { SyncRunItem } from '@/composables/useSyncHistory'
import { Logger } from '@/utils/logger'

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
  site_icon_url: string | null
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

interface SiteOption {
  value: string
  label: string
  iconUrl?: string | null
}

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

interface UseSyncCenterOptions {
  autoLoadSiteOptions?: boolean
}

export function useSyncCenter(options: UseSyncCenterOptions = {}) {
  const {
    autoLoadSiteOptions = true,
  } = options
  const overview = ref<SyncCenterOverview>(createEmptyOverview())
  const runningPreview = ref<SyncCenterItem[]>([])
  const queuedPreview = ref<SyncCenterItem[]>([])
  const recentRuns = ref<SyncRunItem[]>([])
  const runningPreviewError = ref('')
  const queuedPreviewError = ref('')
  const overviewError = ref('')
  const loadingOverview = ref(false)
  const loadingItems = ref(false)
  const hasLoadedOnce = ref(false)
  const siteOptions = ref<SiteOption[]>([])

  const pageError = computed(() => overviewError.value)

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

    siteOptions.value = deduped
  }

  onMounted(async () => {
    if (autoLoadSiteOptions) {
      await loadSiteOptions()
    }
  })

  return {
    hasLoadedOnce,
    loadingItems,
    loadingOverview,
    overview,
    overviewError,
    pageError,
    queuedPreview,
    queuedPreviewError,
    recentRuns,
    runningPreview,
    runningPreviewError,
    loadSiteOptions,
    siteOptions,
  }
}
