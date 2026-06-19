import { batchUpdateVideoHistory, clearVideoHistory, deleteVideoHistory, listVideoHistory, updateVideoHistory } from '@/shared/api'
import { Logger } from '@/shared/lib/logger'
import { toPersistedVideoId, useVideoHistorySync } from './useVideoHistorySync'
import type { ReportData } from './useVideoHistorySync'

type VideoId = string | number

// ponytail: Network Information API is non-standard; declare the slice we read.
type NetworkInformation = { effectiveType?: string; downlink?: number }
type NavigatorWithConnection = Navigator & { connection?: NetworkInformation }

type SendReportOptions = {
  force?: boolean
  includeMetadata?: boolean
  retryOnFailure?: boolean
}

type WatchHistoryFilters = {
  nsfw?: string
  site?: string
  pageSize?: number
  query?: string
}

export function useVideoHistory() {
  const sync = useVideoHistorySync()

  const sendReport = async (video_id: VideoId, currentTime: number, options: SendReportOptions = {}) => {
    const {
      force = false,
      includeMetadata = false,
      retryOnFailure = true
    } = options
    const persistedVideoId = toPersistedVideoId(video_id)

    const connection = (navigator as NavigatorWithConnection).connection

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

    sync.updateLocalHistory(video_id, reportData)

    if (persistedVideoId == null) {
      sync.removePendingUpdate(video_id)
      return true
    }

    if (sync.syncStatus.isOnline || force) {
      const { error } = await updateVideoHistory({
        ...reportData,
        video_id: persistedVideoId,
      })
      if (!error) {
        sync.syncStatus.lastSyncTime = Date.now()
        sync.syncStatus.failedAttempts = 0

        sync.removePendingUpdate(video_id)

        return true
      }

      Logger.warn('Failed to sync video history', error)
      sync.syncStatus.failedAttempts++

      if (retryOnFailure) {
        sync.addToPendingUpdates(reportData)
      }

      return false
    } else {
      sync.addToPendingUpdates(reportData)
      return false
    }
  }

  const sendBatchReport = async (reports: ReportData[]) => {
    if (!sync.syncStatus.isOnline || reports.length === 0) {
      return false
    }

    const persistedReports = reports
      .map((report) => {
        const persistedVideoId = toPersistedVideoId(report.video_id)
        return persistedVideoId == null
          ? null
          : {
              ...report,
              video_id: persistedVideoId,
            }
      })
      .filter((report): report is ReportData & { video_id: number } => report != null)

    if (persistedReports.length === 0) {
      reports.forEach((report) => {
        sync.removePendingUpdate(report.video_id)
      })
      return true
    }

    const { error } = await batchUpdateVideoHistory(persistedReports)

    if (!error) {
      sync.syncStatus.lastSyncTime = Date.now()
      sync.syncStatus.failedAttempts = 0

      reports.forEach((report) => {
        sync.removePendingUpdate(report.video_id)
      })

      return true
    }

    Logger.error('Failed to batch sync video history', error)
    sync.syncStatus.failedAttempts++
    return false
  }

  const syncPendingUpdates = async () => {
    if (sync.pendingUpdates.value.length === 0 || !sync.syncStatus.isOnline) {
      return false
    }

    const batchSize = 20
    const batches: ReportData[][] = []

    for (let i = 0; i < sync.pendingUpdates.value.length; i += batchSize) {
      batches.push(sync.pendingUpdates.value.slice(i, i + batchSize))
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

  const getWatchHistory = async (page = 1, filters: WatchHistoryFilters = {}) => {
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

    const { data, error } = await listVideoHistory(params)
    // ponytail: callers (History.vue) don't catch — rejecting with the already-
    // shaped ApiError carries the same message the old try/catch/throw re-wrap did.
    if (error) throw error

    const payload = data || { items: [], total: 0, page, page_size: pageSize }
    const items = Array.isArray(payload.items) ? payload.items : []
    return {
      items,
      total: payload.total ?? 0,
      page: payload.page ?? page,
      page_size: payload.page_size ?? pageSize
    }
  }

  const clearHistory = async (videoIds: VideoId[] | null = null) => {
    const { error } = await clearVideoHistory(videoIds)
    if (error) throw error
    return true
  }

  const deleteHistoryEntry = async (historyId: VideoId) => {
    const { error } = await deleteVideoHistory(historyId)
    if (error) throw error
    return true
  }

  return {
    sendReport,
    sendBatchReport,
    getWatchHistory,
    clearHistory,
    deleteHistoryEntry,
    syncPendingUpdates,
    getLocalHistory: sync.getLocalHistory,
    getAllLocalHistory: sync.getAllLocalHistory,
    updateLocalHistory: sync.updateLocalHistory,
    cleanupLocalHistory: sync.cleanupLocalHistory,
    setupNetworkListeners: () => sync.setupNetworkListeners(syncPendingUpdates),
    startPeriodicSync: (interval?: number) => sync.startPeriodicSync(syncPendingUpdates, interval),
    syncStatus: sync.syncStatus,
    pendingUpdates: sync.pendingUpdates,
    localHistory: sync.localHistory,
  }
}
