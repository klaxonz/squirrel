import { ref, type Ref } from 'vue'
import { getRssSyncStatus, syncRssAccount } from '@/shared/api'
import { errorMessage } from '@/shared/lib/errorMessage'
import type { RssSyncStatus } from '@/features/rss/types/rss'

export type { RssSyncStatus }

export interface UseRssSyncOptions {
  selectedAccountId: Ref<number | null>
  onStatus: (message: string, isError?: boolean) => void
  loadAccounts: () => Promise<unknown>
  loadFeeds: () => Promise<unknown>
  loadEntries: (isReset?: boolean) => Promise<unknown>
}

export interface UseRssSyncReturn {
  syncing: Ref<boolean>
  getRssSyncModeLabel: (syncMode?: string) => string
  pollSyncProgress: () => void
  syncSelectedAccount: (forceFullSync?: boolean) => Promise<void>
  resumeSyncPollingIfRunning: () => Promise<void>
  stopSyncPolling: () => void
}

const POLL_INTERVAL_MS = 1000

const getRssSyncModeLabel = (syncMode?: string) => {
  return syncMode === 'full' ? '全量同步' : '轻量同步'
}

const formatRunningStatus = (data: RssSyncStatus) => {
  const phaseLabels: Record<string, string> = {
    starting: '启动中',
    feeds_fetching: '同步订阅源',
    feeds_saving: '同步订阅源',
    entries_fetching: '同步文章',
    entries_saving: '同步文章',
  }
  const modeLabel = getRssSyncModeLabel(data.sync_mode)
  const phaseLabel = (data.phase && phaseLabels[data.phase]) || data.phase || ''
  let progress = ''
  if (data.phase === 'entries_fetching') {
    progress = data.entries_fetched != null ? `已获取 ${data.entries_fetched} 篇` : '等待服务器响应'
  } else if (data.phase === 'entries_saving') {
    progress = `已更新 ${data.entries_synced || 0} 篇`
  } else if (data.feeds_synced != null) {
    progress = `${data.feeds_synced} 个`
  }
  return `${modeLabel}中 [${phaseLabel}] ${progress}`.trim()
}

export function useRssSync(options: UseRssSyncOptions): UseRssSyncReturn {
  const { selectedAccountId, onStatus, loadAccounts, loadFeeds, loadEntries } = options
  const syncing = ref(false)
  let pollTimer: ReturnType<typeof setTimeout> | null = null
  let pollGeneration = 0

  const clearPollTimer = () => {
    if (!pollTimer) return
    clearTimeout(pollTimer)
    pollTimer = null
  }

  const isCurrentPoll = (generation: number, accountId: number) => {
    return generation === pollGeneration && selectedAccountId.value === accountId
  }

  const stopSyncPolling = () => {
    pollGeneration += 1
    clearPollTimer()
    syncing.value = false
  }

  const pollSyncProgress = () => {
    const accountId = selectedAccountId.value
    stopSyncPolling()
    if (!accountId) return

    const generation = pollGeneration
    syncing.value = true

    const poll = async () => {
      try {
        const data = await getRssSyncStatus(accountId)
        if (!isCurrentPoll(generation, accountId)) return

        if (data.running) {
          onStatus(formatRunningStatus(data))
          pollTimer = setTimeout(() => void poll(), POLL_INTERVAL_MS)
          return
        }

        syncing.value = false
        const modeLabel = getRssSyncModeLabel(data.sync_mode)
        if (data.phase === 'completed') {
          const changedEntries = data.entries_synced || 0
          const entryText = changedEntries > 0 ? `已更新 ${changedEntries} 篇文章` : '所有内容已是最新'
          onStatus(`${modeLabel}完成：${entryText}`)
        } else {
          onStatus(data.error || data.message || '同步失败', true)
        }

        await loadAccounts()
        if (!isCurrentPoll(generation, accountId)) return
        await Promise.all([loadFeeds(), loadEntries(true)])
      } catch (err) {
        if (!isCurrentPoll(generation, accountId)) return
        syncing.value = false
        onStatus(errorMessage(err, '同步状态查询失败'), true)
      }
    }

    void poll()
  }

  const syncSelectedAccount = async (forceFullSync = false) => {
    const accountId = selectedAccountId.value
    if (!accountId || syncing.value) return
    syncing.value = true
    onStatus('')
    try {
      const result = await syncRssAccount(accountId, undefined, forceFullSync)
      if (selectedAccountId.value !== accountId) return
      if (!result.started) throw new Error('RSS sync did not start')
      pollSyncProgress()
    } catch (err) {
      if (selectedAccountId.value !== accountId) return
      syncing.value = false
      onStatus(errorMessage(err, '启动同步失败'), true)
    }
  }

  const resumeSyncPollingIfRunning = async () => {
    const accountId = selectedAccountId.value
    stopSyncPolling()
    if (!accountId) return
    try {
      const data = await getRssSyncStatus(accountId)
      if (selectedAccountId.value === accountId && data.running) pollSyncProgress()
    } catch {
      // A resume probe is best-effort; an explicit sync still reports errors.
    }
  }

  return {
    syncing,
    getRssSyncModeLabel,
    pollSyncProgress,
    syncSelectedAccount,
    resumeSyncPollingIfRunning,
    stopSyncPolling,
  }
}

export default useRssSync
