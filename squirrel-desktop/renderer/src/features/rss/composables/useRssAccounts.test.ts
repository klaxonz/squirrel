import { effectScope, nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  createRssAccount,
  getRssAccounts,
  testRssAccount,
  testRssAccountConfig,
  updateRssAccount,
} from '@/shared/api'
import type { RssAccount } from '@/features/rss/types/rss'
import { DEFAULT_RSS_SYNC_ENTRY_LIMIT, useRssAccounts } from './useRssAccounts'

vi.mock('@/shared/api', () => ({
  createRssAccount: vi.fn(),
  deleteRssAccount: vi.fn(),
  getRssAccounts: vi.fn(),
  testRssAccount: vi.fn(),
  testRssAccountConfig: vi.fn(),
  updateRssAccount: vi.fn(),
}))

vi.mock('@/shared/composables/usePointerOutside', () => ({
  usePointerOutside: vi.fn(),
}))

const accountFixture = (overrides: Partial<RssAccount> = {}): RssAccount => ({
  id: 7,
  provider: 'miniflux',
  capabilities: { manage_subscriptions: true },
  name: 'Reader',
  base_url: 'https://reader.example',
  username: null,
  enabled: true,
  sync_entry_limit: 321,
  last_sync_at: null,
  last_error: null,
  created_at: null,
  updated_at: null,
  ...overrides,
})

const deferred = <T>() => {
  let resolve!: (value: T | PromiseLike<T>) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

describe('useRssAccounts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getRssAccounts).mockResolvedValue({ data: [] })
    vi.mocked(testRssAccount).mockResolvedValue({ ok: true, feed_count: 3 })
    vi.mocked(testRssAccountConfig).mockResolvedValue({ ok: true, feed_count: 2 })
  })

  it('supplies the required default sync limit when creating a Miniflux account', async () => {
    const saved = accountFixture({ sync_entry_limit: DEFAULT_RSS_SYNC_ENTRY_LIMIT })
    vi.mocked(createRssAccount).mockResolvedValue(saved)
    const onRefresh = vi.fn().mockResolvedValue(undefined)
    const scope = effectScope()
    const state = scope.run(() => useRssAccounts({ onRefresh }))!

    state.openAddAccount()
    state.accountForm.value.provider = 'miniflux'
    await nextTick()
    Object.assign(state.accountForm.value, {
      base_url: ' https://reader.example/ ',
      credential: 'token',
    })

    expect(state.accountForm.value.sync_entry_limit).toBe(DEFAULT_RSS_SYNC_ENTRY_LIMIT)
    expect(state.canSaveForm.value).toBe(true)
    await state.saveAccount()

    expect(createRssAccount).toHaveBeenCalledWith(expect.objectContaining({
      provider: 'miniflux',
      base_url: 'https://reader.example/',
      sync_entry_limit: DEFAULT_RSS_SYNC_ENTRY_LIMIT,
    }))
    expect(state.selectedAccountId.value).toBe(saved.id)
    expect(onRefresh).toHaveBeenCalledOnce()
    scope.stop()
  })

  it('tests an unchanged saved account without asking for its credential again', async () => {
    const account = accountFixture()
    const scope = effectScope()
    const state = scope.run(() => useRssAccounts())!

    state.openEditAccount(account)
    expect(state.canTestForm.value).toBe(true)
    await state.testForm()

    expect(testRssAccount).toHaveBeenCalledWith(account.id)
    expect(testRssAccountConfig).not.toHaveBeenCalled()
    expect(state.formMessage.value).toContain('3')
    scope.stop()
  })

  it('requires a new credential before testing unsaved connection changes', async () => {
    const account = accountFixture()
    const scope = effectScope()
    const state = scope.run(() => useRssAccounts())!

    state.openEditAccount(account)
    state.accountForm.value.base_url = 'https://new-reader.example'
    await nextTick()
    expect(state.canTestForm.value).toBe(false)
    expect(state.canSaveForm.value).toBe(false)

    state.accountForm.value.credential = 'new-token'
    expect(state.canTestForm.value).toBe(true)
    expect(state.canSaveForm.value).toBe(true)
    await state.testForm()

    expect(testRssAccount).not.toHaveBeenCalled()
    expect(testRssAccountConfig).toHaveBeenCalledWith(expect.objectContaining({
      base_url: 'https://new-reader.example',
      credential: 'new-token',
    }))
    scope.stop()
  })

  it('preserves the configured sync limit on a name-only account update', async () => {
    const account = accountFixture()
    vi.mocked(updateRssAccount).mockResolvedValue({ ...account, name: 'Renamed' })
    const scope = effectScope()
    const state = scope.run(() => useRssAccounts({ onRefresh: vi.fn().mockResolvedValue(undefined) }))!

    state.openEditAccount(account)
    state.accountForm.value.name = 'Renamed'
    await state.saveAccount()

    expect(updateRssAccount).toHaveBeenCalledWith(account.id, expect.objectContaining({
      name: 'Renamed',
      sync_entry_limit: 321,
    }))
    scope.stop()
  })

  it('lets only the latest account request commit data, selection, and loading state', async () => {
    type AccountsResponse = Awaited<ReturnType<typeof getRssAccounts>>
    const staleRequest = deferred<AccountsResponse>()
    const currentRequest = deferred<AccountsResponse>()
    vi.mocked(getRssAccounts)
      .mockImplementationOnce(() => staleRequest.promise)
      .mockImplementationOnce(() => currentRequest.promise)
    const scope = effectScope()
    const state = scope.run(() => useRssAccounts())!

    const staleLoad = state.loadAccounts()
    const currentLoad = state.loadAccounts()
    staleRequest.resolve({ data: [accountFixture({ id: 1, name: 'Stale' })] })
    await staleLoad

    expect(state.loadingAccounts.value).toBe(true)
    expect(state.accounts.value).toEqual([])
    expect(state.selectedAccountId.value).toBeNull()

    const currentAccount = accountFixture({ id: 2, name: 'Current' })
    currentRequest.resolve({ data: [currentAccount] })
    await currentLoad

    expect(state.loadingAccounts.value).toBe(false)
    expect(state.accounts.value).toEqual([currentAccount])
    expect(state.selectedAccountId.value).toBe(currentAccount.id)
    scope.stop()
  })

  it('ignores a stale account failure after the current request succeeds', async () => {
    type AccountsResponse = Awaited<ReturnType<typeof getRssAccounts>>
    const staleRequest = deferred<AccountsResponse>()
    const currentRequest = deferred<AccountsResponse>()
    vi.mocked(getRssAccounts)
      .mockImplementationOnce(() => staleRequest.promise)
      .mockImplementationOnce(() => currentRequest.promise)
    const onStatus = vi.fn()
    const scope = effectScope()
    const state = scope.run(() => useRssAccounts({ onStatus }))!

    const staleLoad = state.loadAccounts()
    const currentLoad = state.loadAccounts()
    const currentAccount = accountFixture({ id: 3, name: 'Current' })
    currentRequest.resolve({ data: [currentAccount] })
    await currentLoad
    staleRequest.reject(new Error('stale account failure'))
    await staleLoad

    expect(state.accounts.value).toEqual([currentAccount])
    expect(state.selectedAccountId.value).toBe(currentAccount.id)
    expect(state.accountsError.value).toBe('')
    expect(state.loadingAccounts.value).toBe(false)
    expect(onStatus).not.toHaveBeenCalled()
    scope.stop()
  })
})
