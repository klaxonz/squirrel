import { reactive, ref } from 'vue'
import { batchUpdateVideoHistory, clearVideoHistory, listVideoHistory, updateVideoHistory } from '@/api'
import { Logger } from '@/utils/logger'

type VideoId = string | number
type ApiResult<T> = { data?: T | null; error?: any }

type ReportConnection = {
  effectiveType?: string
  downlink?: number
}

type ReportData = {
  video_id: VideoId
  last_position: number
  timestamp: number
  user_agent?: string
  viewport?: { width: number; height: number }
  connection?: ReportConnection | null
  lastUpdated?: number
  [key: string]: unknown
}

type SyncStatus = {
  isOnline: boolean
  lastSyncTime: number | null
  failedAttempts: number
}

type SendReportOptions = {
  force?: boolean
  includeMetadata?: boolean
  retryOnFailure?: boolean
}

export default function useVideoHistory() {
  const localHistory = reactive(new Map<VideoId, ReportData>()) as Map<VideoId, ReportData>
  const pendingUpdates = ref<ReportData[]>([])

  const syncStatus = reactive<SyncStatus>({
    isOnline: navigator.onLine,
    lastSyncTime: null,
    failedAttempts: 0
  })

  const sendReport = async (video_id: VideoId, currentTime: number, options: SendReportOptions = {}) => {
    const {
      force = false,
      includeMetadata = false,
      retryOnFailure = true
    } = options

    const connection = (navigator as any).connection as ReportConnection | undefined

    const reportData: ReportData = {
      video_id,
      last_position: currentTime,
      timestamp: Date.now(),
      ...(includeMetadata && {
        user_agent: navigator.userAgent,
        viewport: {
          width: window.innerWidth,
          height: window.innerHeight
        },
        connection: connection
          ? {
              effectiveType: connection.effectiveType,
              downlink: connection.downlink
            }
          : null
      })
    }

    updateLocalHistory(video_id, reportData)

    if (syncStatus.isOnline || force) {
      const { error } = (await updateVideoHistory(reportData)) as ApiResult<unknown>
      if (!error) {
        syncStatus.lastSyncTime = Date.now()
        syncStatus.failedAttempts = 0

        removePendingUpdate(video_id)

        return true
      }

      Logger.warn('Failed to sync video history', error)
      syncStatus.failedAttempts++

      if (retryOnFailure) {
        addToPendingUpdates(reportData)
      }

      return false
    } else {
      addToPendingUpdates(reportData)
      return false
    }
  }

  const sendBatchReport = async (reports: ReportData[]) => {
    if (!syncStatus.isOnline || reports.length === 0) {
      return false
    }

    const { error } = (await batchUpdateVideoHistory(reports)) as ApiResult<unknown>

    if (!error) {
      syncStatus.lastSyncTime = Date.now()
      syncStatus.failedAttempts = 0

      reports.forEach((report) => {
        removePendingUpdate(report.video_id)
      })

      return true
    }

    Logger.error('Failed to batch sync video history', error)
    syncStatus.failedAttempts++
    return false
  }

  type WatchHistoryFilters = {
    nsfw?: string
    site?: string
    pageSize?: number
    query?: string
  }

  const getWatchHistory = async (page = 1, filters: WatchHistoryFilters = {}) => {
    try {
      const { nsfw, site, pageSize = 20, query } = filters
      const params: Record<string, unknown> = { page, page_size: pageSize }
      
      if (nsfw && nsfw !== 'all') {
        params.nsfw = nsfw
      }
      if (site && site !== 'all') {
        params.site = site
      }
      if (query) {
        params.query = query
      }
      
      const { data, error } = (await listVideoHistory(params)) as ApiResult<any>
      if (error) {
        const message = typeof error?.message === 'string' ? error.message : '加载历史失败'
        throw new Error(message)
      }

      const payload = data || {}
      const items = Array.isArray(payload.items) ? payload.items : []
      return {
        items,
        total: payload.total ?? 0,
        page: payload.page ?? page,
        page_size: payload.page_size ?? pageSize
      }
    } catch (error: unknown) {
      const message = typeof (error as any)?.message === 'string' ? (error as any).message : '加载历史失败'
      throw new Error(message)
    }
  }

  const clearHistory = async (videoIds: VideoId[] | null = null) => {
    try {
      const { error } = (await clearVideoHistory(videoIds)) as ApiResult<unknown>
      if (error) {
        const message = typeof error?.message === 'string' ? error.message : '清空历史失败'
        throw new Error(message)
      }
      return true;
    } catch (error: unknown) {
      const message = typeof (error as any)?.message === 'string' ? (error as any).message : '清空历史失败'
      throw new Error(message)
    }
  }

  const getLocalHistory = (video_id: VideoId) => {
    return localHistory.get(video_id)
  }

  const getAllLocalHistory = () => {
    return Array.from(localHistory.values())
  }

  const updateLocalHistory = (video_id: VideoId, data: ReportData) => {
    localHistory.set(video_id, {
      ...data,
      lastUpdated: Date.now(),
    })
  }

  const addToPendingUpdates = (reportData: ReportData) => {
    const existingIndex = pendingUpdates.value.findIndex(
      (update) => update.video_id === reportData.video_id
    )

    if (existingIndex !== -1) {
      pendingUpdates.value[existingIndex] = reportData
    } else {
      pendingUpdates.value.push(reportData)
    }

    if (pendingUpdates.value.length > 100) {
      pendingUpdates.value = pendingUpdates.value.slice(-100)
    }
  }

  const removePendingUpdate = (video_id: VideoId) => {
    const index = pendingUpdates.value.findIndex(
      (update) => update.video_id === video_id
    )
    if (index !== -1) {
      pendingUpdates.value.splice(index, 1)
    }
  }

  const syncPendingUpdates = async () => {
    if (pendingUpdates.value.length === 0 || !syncStatus.isOnline) {
      return false
    }

    const batchSize = 20
    const batches: ReportData[][] = []

    for (let i = 0; i < pendingUpdates.value.length; i += batchSize) {
      batches.push(pendingUpdates.value.slice(i, i + batchSize))
    }

    let successCount = 0
    for (const batch of batches) {
      const success = await sendBatchReport(batch)
      if (success) {
        successCount += batch.length
      }
    }

    return successCount
  }

  const cleanupLocalHistory = (maxAge = 7 * 24 * 60 * 60 * 1000) => {
    const now = Date.now()
    const toDelete: VideoId[] = []

    for (const [video_id, data] of localHistory.entries()) {
      const lastUpdated = data.lastUpdated || 0
      if (now - lastUpdated > maxAge) {
        toDelete.push(video_id)
      }
    }

    toDelete.forEach((video_id) => {
      localHistory.delete(video_id)
    })

    return toDelete.length
  }

  const setupNetworkListeners = () => {
    const handleOnline = () => {
      syncStatus.isOnline = true
      Logger.debug('Network online, syncing pending updates')
      syncPendingUpdates()
    }

    const handleOffline = () => {
      syncStatus.isOnline = false
      Logger.debug('Network offline, updates will be queued')
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }

  const startPeriodicSync = (interval = 30000) => {
    const syncInterval = setInterval(() => {
      if (syncStatus.isOnline && pendingUpdates.value.length > 0) {
        syncPendingUpdates()
      }

      if (Math.random() < 0.1) {
        cleanupLocalHistory()
      }
    }, interval)

    return () => clearInterval(syncInterval)
  }

  return {
    sendReport,
    sendBatchReport,
    getWatchHistory,
    clearHistory,
    getLocalHistory,
    getAllLocalHistory,
    updateLocalHistory,
    syncPendingUpdates,
    cleanupLocalHistory,
    setupNetworkListeners,
    startPeriodicSync,
    syncStatus,
    pendingUpdates,
    localHistory,
  }
}
