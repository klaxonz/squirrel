import { reactive, ref } from 'vue'
import { Logger } from '@/shared/lib/logger'

type VideoId = string | number

export type ReportData = {
  video_id: VideoId
  last_position: number
  timestamp: number
  user_agent?: string
  viewport?: { width: number; height: number }
  connection?: ReportConnection | null
  lastUpdated?: number
  [key: string]: unknown
}

type ReportConnection = {
  effectiveType?: string
  downlink?: number
}

type SyncStatus = {
  isOnline: boolean
  lastSyncTime: number | null
  failedAttempts: number
}

export const toPersistedVideoId = (videoId: VideoId) => {
  const numericId = Number(videoId)
  return Number.isSafeInteger(numericId) && numericId > 0 ? numericId : null
}

export function useVideoHistorySync() {
  const localHistory = reactive(new Map<VideoId, ReportData>()) as Map<VideoId, ReportData>
  const pendingUpdates = ref<ReportData[]>([])

  const syncStatus = reactive<SyncStatus>({
    isOnline: navigator.onLine,
    lastSyncTime: null,
    failedAttempts: 0,
  })

  const getLocalHistory = (video_id: VideoId) => {
    return localHistory.get(video_id)
  }

  const getAllLocalHistory = () => {
    return Array.from(localHistory.values())
  }

  const updateLocalHistory = (video_id: VideoId, report: ReportData) => {
    localHistory.set(video_id, {
      ...report,
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

  const setupNetworkListeners = (onSync: () => Promise<unknown>) => {
    const handleOnline = () => {
      syncStatus.isOnline = true
      Logger.debug('Network online, syncing pending updates')
      onSync()
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

  const startPeriodicSync = (onSync: () => Promise<unknown>, interval = 30000) => {
    const syncInterval = setInterval(() => {
      if (syncStatus.isOnline && pendingUpdates.value.length > 0) {
        onSync()
      }

      if (Math.random() < 0.1) {
        cleanupLocalHistory()
      }
    }, interval)

    return () => clearInterval(syncInterval)
  }

  return {
    localHistory,
    pendingUpdates,
    syncStatus,
    getLocalHistory,
    getAllLocalHistory,
    updateLocalHistory,
    addToPendingUpdates,
    removePendingUpdate,
    cleanupLocalHistory,
    setupNetworkListeners,
    startPeriodicSync,
  }
}
