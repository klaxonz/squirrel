import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { getExtractionCenterItems, getExtractionCenterOverview } from '@/api'
import type { SyncCenterItem, SyncCenterOverview } from '@/composables/useSyncCenter'
import { Logger } from '@/utils/logger'

interface ExtractionCenterListResponse {
  total: number
  page: number
  pageSize: number
  data: SyncCenterItem[]
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

interface UseExtractionCenterOptions {
  autoLoad?: boolean
  autoStartPolling?: boolean
}

export function useExtractionCenter(options: UseExtractionCenterOptions = {}) {
  const {
    autoLoad = true,
    autoStartPolling = true,
  } = options
  const overview = ref<SyncCenterOverview>(createEmptyOverview())
  const runningPreview = ref<SyncCenterItem[]>([])
  const queuedPreview = ref<SyncCenterItem[]>([])
  const recentPreview = ref<SyncCenterItem[]>([])
  const overviewError = ref('')
  const runningPreviewError = ref('')
  const queuedPreviewError = ref('')
  const recentPreviewError = ref('')
  const loadingOverview = ref(false)
  const loadingItems = ref(false)
  const hasLoadedOnce = ref(false)
  const pollingEnabled = ref(true)
  const lastUpdatedAt = ref('')

  let pollTimer: ReturnType<typeof setInterval> | null = null
  let overviewRequestSeq = 0
  let runningRequestSeq = 0
  let queuedRequestSeq = 0
  let recentRequestSeq = 0

  const pageError = computed(() => {
    return overviewError.value || runningPreviewError.value || queuedPreviewError.value || recentPreviewError.value
  })

  const updateLastRefreshTime = () => {
    lastUpdatedAt.value = new Date().toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  const loadOverview = async () => {
    const requestSeq = ++overviewRequestSeq
    loadingOverview.value = true
    overviewError.value = ''
    const { data, error } = await getExtractionCenterOverview<SyncCenterOverview>()
    if (requestSeq !== overviewRequestSeq) {
      return
    }
    if (error) {
      overviewError.value = error.message || '加载视频提取总览失败'
      Logger.error('Failed to load extraction center overview', error)
    } else if (data) {
      overview.value = {
        ...createEmptyOverview(),
        ...data,
      }
    }
    loadingOverview.value = false
  }

  const loadPreview = async (status: 'running' | 'queued' | 'recent') => {
    const requestSeq = status === 'running'
      ? ++runningRequestSeq
      : status === 'queued'
        ? ++queuedRequestSeq
        : ++recentRequestSeq

    const { data, error } = await getExtractionCenterItems<ExtractionCenterListResponse>({
      status,
      page: 1,
      pageSize: 100,
    })

    const isStale = status === 'running'
      ? requestSeq !== runningRequestSeq
      : status === 'queued'
        ? requestSeq !== queuedRequestSeq
        : requestSeq !== recentRequestSeq
    if (isStale) {
      return
    }

    if (error) {
      Logger.error(`Failed to load extraction ${status} preview`, error)
      const message = error.message || '加载视频提取预览失败'
      if (status === 'running') {
        runningPreviewError.value = message
        runningPreview.value = []
      } else if (status === 'queued') {
        queuedPreviewError.value = message
        queuedPreview.value = []
      } else {
        recentPreviewError.value = message
        recentPreview.value = []
      }
      return
    }

    const nextItems = data?.data || []
    if (status === 'running') {
      runningPreviewError.value = ''
      runningPreview.value = nextItems
    } else if (status === 'queued') {
      queuedPreviewError.value = ''
      queuedPreview.value = nextItems
    } else {
      recentPreviewError.value = ''
      recentPreview.value = nextItems
    }
  }

  const refreshAll = async () => {
    loadingItems.value = true
    await Promise.all([
      loadOverview(),
      loadPreview('running'),
      loadPreview('queued'),
      loadPreview('recent'),
    ])
    loadingItems.value = false
    hasLoadedOnce.value = true
    updateLastRefreshTime()
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

  onMounted(async () => {
    if (!autoLoad) {
      if (autoStartPolling) {
        startPolling()
      }
      return
    }

    await refreshAll()

    if (autoStartPolling) {
      startPolling()
    }
  })

  onUnmounted(() => {
    clearPollTimer()
  })

  return {
    hasLoadedOnce,
    lastUpdatedAt,
    loadingItems,
    loadingOverview,
    overview,
    overviewError,
    pageError,
    queuedPreview,
    queuedPreviewError,
    recentPreview,
    recentPreviewError,
    refreshAll,
    runningPreview,
    runningPreviewError,
    setPollingEnabled,
  }
}
