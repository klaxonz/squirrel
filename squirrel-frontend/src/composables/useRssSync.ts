import { ref } from 'vue'
import type { Ref } from 'vue'
import { onClickOutside } from '@vueuse/core'
import { getRssSyncStatus, syncRssAccount } from '@/api'
import type { RssSyncStatus } from '@/types/rss'

export type { RssSyncStatus }

export interface UseRssSyncOptions {
  selectedAccountId: Ref<string | number | null>
  onStatus: (message: string, isError?: boolean) => void
  // completion loaders — called in order when a sync finishes
  loadAccounts: () => Promise<unknown>
  loadFeeds: () => Promise<unknown>
  loadEntries: (isReset?: boolean) => Promise<unknown>
}

export interface UseRssSyncReturn {
  syncing: Ref<boolean>
  showSyncMenu: Ref<boolean>
  syncDropdownRef: Ref<HTMLElement | null>
  getRssSyncModeLabel: (syncMode?: string) => string
  pollSyncProgress: () => void
  syncSelectedAccount: (forceFullSync?: boolean) => Promise<void>
  resumeSyncPollingIfRunning: () => Promise<void>
  stopSyncPolling: () => void
}

const getRssSyncModeLabel = (syncMode?: string) => {
  return syncMode === 'full' ? '全量同步' : '轻量同步'
}

export function useRssSync(options: UseRssSyncOptions): UseRssSyncReturn {
  const { selectedAccountId, onStatus, loadAccounts, loadFeeds, loadEntries } = options

  const syncing = ref(false)
  const showSyncMenu = ref(false)
  const syncDropdownRef = ref<HTMLElement | null>(null)
  let syncPollTimer: ReturnType<typeof setInterval> | null = null

  // ponytail: click-outside lives with the dropdown ref it guards; the parent
  // no longer needs to wire onClickOutside for the sync menu.
  onClickOutside(syncDropdownRef, () => {
    showSyncMenu.value = false
  })

  const pollSyncProgress = () => {
    if (syncPollTimer) clearInterval(syncPollTimer)
    const accountId = selectedAccountId.value
    if (!accountId) {
      syncing.value = false
      return
    }

    syncPollTimer = setInterval(async () => {
      const result = await getRssSyncStatus(accountId)
      if (result.error) {
        clearInterval(syncPollTimer!)
        syncPollTimer = null
        syncing.value = false
        onStatus(result.error.message, true)
        return
      }
      const data = result.data
      if (!data) return
      const modeLabel = getRssSyncModeLabel(data.sync_mode)
      if (data.running) {
        const phaseLabel: Record<string, string> = {
          starting: '启动中',
          feeds_fetching: '同步订阅源',
          feeds_saving: '同步订阅源',
          entries_fetching: '同步文章',
          entries_saving: '同步文章',
        }
        const label = (data.phase && phaseLabel[data.phase]) || data.phase || ''
        let progress = ''
        if (data.phase === 'entries_fetching') {
          progress = data.entries_fetched != null ? `已获取 ${data.entries_fetched} 篇` : '等待服务器响应...'
        } else if (data.phase === 'entries_saving') {
          progress = `已更新 ${data.entries_synced || 0} 篇`
        } else if (data.feeds_synced != null) {
          progress = `${data.feeds_synced} 个`
        }
        onStatus(`${modeLabel}中 [${label}] ${progress}`, false)
      } else {
        clearInterval(syncPollTimer!)
        syncPollTimer = null
        syncing.value = false
        if (data.phase === 'completed') {
          const changedEntries = data.entries_synced || 0
          const entryText = changedEntries > 0 ? `已更新 ${changedEntries} 篇文章` : '所有内容已是最新'
          onStatus(`${modeLabel}完成：${entryText}`)
        } else {
          onStatus(data.message || data.error || '同步失败', true)
        }
        await loadAccounts()
        await loadFeeds()
        await loadEntries(true)
      }
    }, 1000)
  }

  const syncSelectedAccount = async (forceFullSync = false) => {
    if (!selectedAccountId.value) return
    syncing.value = true
    onStatus('')
    const result = await syncRssAccount(selectedAccountId.value, undefined, forceFullSync)
    if (result.error) {
      syncing.value = false
      onStatus(result.error.message, true)
      return
    }
    pollSyncProgress()
  }

  const resumeSyncPollingIfRunning = async () => {
    const accountId = selectedAccountId.value
    if (!accountId) return
    const result = await getRssSyncStatus(accountId)
    if (result.error) return
    const data = result.data
    if (data && data.running) {
      syncing.value = true
      pollSyncProgress()
    }
  }

  const stopSyncPolling = () => {
    if (syncPollTimer) {
      clearInterval(syncPollTimer)
      syncPollTimer = null
    }
  }

  return {
    syncing,
    showSyncMenu,
    syncDropdownRef,
    getRssSyncModeLabel,
    pollSyncProgress,
    syncSelectedAccount,
    resumeSyncPollingIfRunning,
    stopSyncPolling,
  }
}

export default useRssSync
