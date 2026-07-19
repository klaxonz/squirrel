import { ref } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { getRssSyncStatus, syncRssAccount } from '@/shared/api'
import type { RssSyncStatus } from '@/features/rss/types/rss'
import { useRssSync } from './useRssSync'

vi.mock('@/shared/api', () => ({
  getRssSyncStatus: vi.fn(),
  syncRssAccount: vi.fn(),
}))

const flushPromises = () => new Promise<void>((resolve) => queueMicrotask(resolve))

const createHarness = () => {
  const selectedAccountId = ref<number | null>(1)
  const onStatus = vi.fn()
  const loadAccounts = vi.fn().mockResolvedValue(undefined)
  const loadFeeds = vi.fn().mockResolvedValue(undefined)
  const loadEntries = vi.fn().mockResolvedValue(undefined)
  const state = useRssSync({ selectedAccountId, onStatus, loadAccounts, loadFeeds, loadEntries })
  return { selectedAccountId, onStatus, loadAccounts, loadFeeds, loadEntries, state }
}

describe('useRssSync', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('polls immediately after the server atomically acknowledges a sync start', async () => {
    vi.mocked(syncRssAccount).mockResolvedValue({ started: true, account_id: 1 })
    vi.mocked(getRssSyncStatus).mockResolvedValue({ running: true, phase: 'entries_fetching', entries_fetched: 8 })
    const { state, onStatus } = createHarness()

    await state.syncSelectedAccount()
    await flushPromises()

    expect(syncRssAccount).toHaveBeenCalledWith(1, undefined, false)
    expect(getRssSyncStatus).toHaveBeenCalledWith(1)
    expect(state.syncing.value).toBe(true)
    expect(onStatus).toHaveBeenLastCalledWith(expect.stringContaining('已获取 8 篇'))
    state.stopSyncPolling()
  })

  it('ignores an old account poll that resolves after the account changes', async () => {
    let resolveStatus!: (status: RssSyncStatus) => void
    vi.mocked(getRssSyncStatus).mockImplementationOnce(() => new Promise((resolve) => {
      resolveStatus = resolve
    }))
    const harness = createHarness()

    harness.state.pollSyncProgress()
    harness.selectedAccountId.value = 2
    harness.state.stopSyncPolling()
    resolveStatus({ running: false, phase: 'completed', entries_synced: 4 })
    await flushPromises()

    expect(harness.loadAccounts).not.toHaveBeenCalled()
    expect(harness.loadFeeds).not.toHaveBeenCalled()
    expect(harness.loadEntries).not.toHaveBeenCalled()
    expect(harness.onStatus).not.toHaveBeenCalled()
  })

  it('refreshes account, feed, and entry state when the current sync completes', async () => {
    vi.mocked(getRssSyncStatus).mockResolvedValue({
      running: false,
      phase: 'completed',
      sync_mode: 'full',
      entries_synced: 5,
    })
    const harness = createHarness()

    harness.state.pollSyncProgress()
    await flushPromises()
    await flushPromises()

    expect(harness.state.syncing.value).toBe(false)
    expect(harness.onStatus).toHaveBeenCalledWith('全量同步完成：已更新 5 篇文章')
    expect(harness.loadAccounts).toHaveBeenCalledOnce()
    expect(harness.loadFeeds).toHaveBeenCalledOnce()
    expect(harness.loadEntries).toHaveBeenCalledWith(true)
  })
})
