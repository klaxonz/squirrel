import { LocalStorageAdapter, type IPlayerAdapter, type PlaybackProgress, type ErrorReport } from './PlayerAdapter'
import { updateVideoHistory } from '@/api/videoHistory'
import { playerLogger } from './logger'

export class BackendPlayerAdapter extends LocalStorageAdapter implements IPlayerAdapter {
  private pendingProgress: (PlaybackProgress & { retryCount?: number })[] = []
  private storeKey: string

  constructor(storeKey = 'sp-player-config') {
    super({ configKey: storeKey })
    this.storeKey = storeKey
  }

  async saveProgress(progress: PlaybackProgress): Promise<void> {
    await super.saveProgress(progress)

    const numericId = Number(progress.progressKey)
    if (!Number.isSafeInteger(numericId) || numericId <= 0) return

    this.pendingProgress.push({ ...progress, retryCount: 0 })
    if (this.pendingProgress.length > 20) {
      this.pendingProgress = this.pendingProgress.slice(-20)
    }

    this.debouncedSync()
  }

  private syncPendingAt: number = 0
  private syncTimerHandle: ReturnType<typeof setTimeout> | null = null

  private debouncedSync(): void {
    const now = Date.now()
    if (now - this.syncPendingAt < 5000) {
      if (!this.syncTimerHandle) {
        this.syncTimerHandle = setTimeout(() => {
          this.syncTimerHandle = null
          this.flushPending()
        }, 5000 - (now - this.syncPendingAt))
      }
      return
    }
    this.flushPending()
  }

  private async flushPending(): Promise<void> {
    if (this.pendingProgress.length === 0) return

    const toSync = [...this.pendingProgress]
    this.pendingProgress = []
    this.syncPendingAt = Date.now()

    for (const progress of toSync) {
      const numericId = Number(progress.progressKey)
      if (!Number.isSafeInteger(numericId) || numericId <= 0) continue

      try {
        await updateVideoHistory({
          video_id: numericId,
          last_position: Math.round(progress.currentTime),
          timestamp: progress.timestamp,
        })
      } catch {
        const retryCount = (progress.retryCount ?? 0) + 1
        if (retryCount >= 3) {
          playerLogger.warn('[BackendPlayerAdapter] Discarding progress after 3 retries', {
            videoId: numericId,
            position: Math.round(progress.currentTime),
          })
          continue
        }
        this.pendingProgress.push({ ...progress, retryCount })
      }
    }
  }

  async reportError(report: ErrorReport): Promise<void> {
    playerLogger.warn('[BackendPlayerAdapter] Error', {
      code: report.errorCode,
      message: report.errorMessage,
      sourceUrl: report.sourceUrl,
    })
  }

  destroy(): void {
    this.flushPending()
    if (this.syncTimerHandle) {
      clearTimeout(this.syncTimerHandle)
      this.syncTimerHandle = null
    }
  }
}
