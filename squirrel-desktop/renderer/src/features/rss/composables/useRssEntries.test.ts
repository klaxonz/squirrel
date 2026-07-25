import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, nextTick, ref } from 'vue'
import { getRssEntries, getRssRecentlyViewed, updateRssEntries, updateRssEntry } from '@/shared/api'
import type { RecentEntry, RssEntry } from '@/features/rss/types/rss'
import { useRssEntries } from './useRssEntries'

vi.mock('@/shared/api', () => ({
  getRssEntries: vi.fn().mockResolvedValue({ data: [], total: 0 }),
  getRssRecentlyViewed: vi.fn().mockResolvedValue({ data: [] }),
  recordRssEntryView: vi.fn(),
  updateRssEntries: vi.fn(),
  updateRssEntry: vi.fn(),
}))

const deferred = <T>() => {
  let resolve!: (value: T | PromiseLike<T>) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

describe('useRssEntries', () => {
  beforeEach(() => {
    const values = new Map<string, string>()
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key),
      clear: () => values.clear(),
    })
    vi.clearAllMocks()
    vi.mocked(getRssEntries).mockResolvedValue({ data: [], total: 0, page: 1, pageSize: 30 })
    vi.mocked(getRssRecentlyViewed).mockResolvedValue({ data: [] })
    vi.mocked(updateRssEntries).mockResolvedValue({ updated: 1 })
    vi.mocked(updateRssEntry).mockImplementation(async (_id, payload) => ({
      ...entryFixture(),
      is_read: payload.isRead ?? false,
      is_starred: payload.isStarred ?? false,
    }))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('defaults to the all entries filter', () => {
    const scope = effectScope()
    const { activeFilter, defaultEntryFilter } = scope.run(() => useRssEntries({
      selectedAccountId: ref(null),
      selectedFeedId: ref(null),
      feeds: ref([]),
      searchQuery: ref(''),
      searchTrigger: ref(0),
      getFeedTitle: () => '',
    }))!

    expect(activeFilter.value).toBe('all')
    expect(defaultEntryFilter.value).toBe('all')
    scope.stop()
  })

  it('restores the preferred default entry filter from localStorage', () => {
    localStorage.setItem('rss_default_entry_filter', 'unread')
    const scope = effectScope()
    const { activeFilter, defaultEntryFilter } = scope.run(() => useRssEntries({
      selectedAccountId: ref(null),
      selectedFeedId: ref(null),
      feeds: ref([]),
      searchQuery: ref(''),
      searchTrigger: ref(0),
      getFeedTitle: () => '',
    }))!

    expect(defaultEntryFilter.value).toBe('unread')
    expect(activeFilter.value).toBe('unread')
    scope.stop()
  })

  it('persists the preferred default entry filter without forcing the active filter', () => {
    const scope = effectScope()
    const state = scope.run(() => useRssEntries({
      selectedAccountId: ref(null),
      selectedFeedId: ref(null),
      feeds: ref([]),
      searchQuery: ref(''),
      searchTrigger: ref(0),
      getFeedTitle: () => '',
    }))!

    state.activeFilter.value = 'starred'
    state.setDefaultEntryFilter('unread')

    expect(state.defaultEntryFilter.value).toBe('unread')
    expect(state.activeFilter.value).toBe('starred')
    expect(localStorage.getItem('rss_default_entry_filter')).toBe('unread')

    state.resetActiveFilterToDefault()
    expect(state.activeFilter.value).toBe('unread')
    scope.stop()
  })

  it('sends the article query to the paginated entries API', async () => {
    const scope = effectScope()
    const { loadEntries } = scope.run(() => useRssEntries({
      selectedAccountId: ref(1),
      selectedFeedId: ref(null),
      feeds: ref([]),
      searchQuery: ref('security'),
      searchTrigger: ref(0),
      getFeedTitle: () => '',
    }))!

    await loadEntries(true)

    expect(getRssEntries).toHaveBeenCalledWith(expect.objectContaining({
      accountId: 1,
      query: 'security',
      page: 1,
      pageSize: 30,
    }))
    scope.stop()
  })

  it('starts in skeleton loading state and blocks pagination during a reset', async () => {
    type EntriesResponse = Awaited<ReturnType<typeof getRssEntries>>
    let resolveRequest!: (value: EntriesResponse) => void
    vi.mocked(getRssEntries).mockImplementationOnce(
      () => new Promise<EntriesResponse>((resolve) => {
        resolveRequest = resolve
      }),
    )

    const scope = effectScope()
    const state = scope.run(() => useRssEntries({
      selectedAccountId: ref(1),
      selectedFeedId: ref(null),
      feeds: ref([]),
      searchQuery: ref(''),
      searchTrigger: ref(0),
      getFeedTitle: () => '',
    }))!

    expect(state.loadingEntries.value).toBe(true)

    state.totalEntries.value = 60
    const loading = state.loadEntries(true)

    expect(state.loadingEntries.value).toBe(true)
    expect(state.loadingMoreEntries.value).toBe(false)
    expect(state.totalEntries.value).toBe(0)
    expect(state.hasMoreEntries.value).toBe(false)

    await state.loadMore()
    expect(getRssEntries).toHaveBeenCalledTimes(1)

    resolveRequest({
      data: [],
      total: 0,
      page: 1,
      pageSize: 30,
    })
    await loading

    expect(state.loadingEntries.value).toBe(false)
    scope.stop()
  })

  it('scopes recently viewed entries to the selected account', async () => {
    const scope = effectScope()
    const state = scope.run(() => useRssEntries({
      selectedAccountId: ref(9),
      selectedFeedId: ref(null),
      feeds: ref([]),
      searchQuery: ref(''),
      searchTrigger: ref(0),
      getFeedTitle: () => '',
    }))!

    await state.loadRecentlyViewed()

    expect(getRssRecentlyViewed).toHaveBeenCalledWith(9)
    scope.stop()
  })

  it('does not commit an entry result after the selected account changes', async () => {
    type EntriesResponse = Awaited<ReturnType<typeof getRssEntries>>
    const staleRequest = deferred<EntriesResponse>()
    vi.mocked(getRssEntries).mockImplementationOnce(() => staleRequest.promise)
    const selectedAccountId = ref<number | null>(1)
    const scope = effectScope()
    const state = scope.run(() => useRssEntries({
      selectedAccountId,
      selectedFeedId: ref(null),
      feeds: ref([]),
      searchQuery: ref(''),
      searchTrigger: ref(0),
      getFeedTitle: () => '',
    }))!

    const loading = state.loadEntries(true)
    selectedAccountId.value = 2
    staleRequest.resolve({
      data: [entryFixture({ id: 11, account_id: 1 })],
      total: 1,
      page: 1,
      pageSize: 30,
    })
    await loading

    expect(state.entries.value).toEqual([])
    expect(state.totalEntries.value).toBe(0)
    expect(state.loadingEntries.value).toBe(true)
    scope.stop()
  })

  it('ignores an old entry failure after the new account has loaded', async () => {
    type EntriesResponse = Awaited<ReturnType<typeof getRssEntries>>
    const staleRequest = deferred<EntriesResponse>()
    const currentRequest = deferred<EntriesResponse>()
    vi.mocked(getRssEntries)
      .mockImplementationOnce(() => staleRequest.promise)
      .mockImplementationOnce(() => currentRequest.promise)
    const selectedAccountId = ref<number | null>(1)
    const onStatus = vi.fn()
    const scope = effectScope()
    const state = scope.run(() => useRssEntries({
      selectedAccountId,
      selectedFeedId: ref(null),
      feeds: ref([]),
      searchQuery: ref(''),
      searchTrigger: ref(0),
      getFeedTitle: () => '',
      onStatus,
    }))!

    const staleLoad = state.loadEntries(true)
    selectedAccountId.value = 2
    const currentLoad = state.loadEntries(true)
    const currentEntry = entryFixture({ id: 22, account_id: 2 })
    currentRequest.resolve({ data: [currentEntry], total: 1, page: 1, pageSize: 30 })
    await currentLoad
    staleRequest.reject(new Error('stale entry failure'))
    await staleLoad

    expect(state.entries.value).toEqual([currentEntry])
    expect(state.totalEntries.value).toBe(1)
    expect(state.entriesError.value).toBe('')
    expect(state.loadingEntries.value).toBe(false)
    expect(onStatus).not.toHaveBeenCalled()
    scope.stop()
  })

  it('ignores a recently-viewed failure after the selected account changes', async () => {
    type RecentResponse = Awaited<ReturnType<typeof getRssRecentlyViewed>>
    const staleRequest = deferred<RecentResponse>()
    vi.mocked(getRssRecentlyViewed).mockImplementationOnce(() => staleRequest.promise)
    const selectedAccountId = ref<number | null>(1)
    const onStatus = vi.fn()
    const scope = effectScope()
    const state = scope.run(() => useRssEntries({
      selectedAccountId,
      selectedFeedId: ref(null),
      feeds: ref([]),
      searchQuery: ref(''),
      searchTrigger: ref(0),
      getFeedTitle: () => '',
      onStatus,
    }))!
    const currentEntry: RecentEntry = {
      ...entryFixture({ id: 33, account_id: 2 }),
      viewed_at: '2026-07-20T00:00:00.000Z',
    }

    const staleLoad = state.loadRecentlyViewed()
    selectedAccountId.value = 2
    state.recentlyViewed.value = [currentEntry]
    staleRequest.reject(new Error('stale recent failure'))
    await staleLoad

    expect(state.recentlyViewed.value).toEqual([currentEntry])
    expect(state.entriesError.value).toBe('')
    expect(onStatus).not.toHaveBeenCalled()
    scope.stop()
  })

  it('ignores a superseded pagination failure without rolling back current state', async () => {
    type EntriesResponse = Awaited<ReturnType<typeof getRssEntries>>
    const staleRequest = deferred<EntriesResponse>()
    const currentRequest = deferred<EntriesResponse>()
    vi.mocked(getRssEntries)
      .mockImplementationOnce(() => staleRequest.promise)
      .mockImplementationOnce(() => currentRequest.promise)
    const onStatus = vi.fn()
    const scope = effectScope()
    const state = scope.run(() => useRssEntries({
      selectedAccountId: ref(1),
      selectedFeedId: ref(null),
      feeds: ref([]),
      searchQuery: ref(''),
      searchTrigger: ref(0),
      getFeedTitle: () => '',
      onStatus,
    }))!
    state.loadingEntries.value = false
    state.entries.value = [entryFixture()]
    state.totalEntries.value = 60

    const staleLoad = state.loadMore()
    const currentLoad = state.loadEntries(true)
    const currentEntry = entryFixture({ id: 44 })
    currentRequest.resolve({ data: [currentEntry], total: 1, page: 1, pageSize: 30 })
    await currentLoad
    staleRequest.reject(new Error('stale pagination failure'))
    await staleLoad

    expect(state.entries.value).toEqual([currentEntry])
    expect(state.page.value).toBe(1)
    expect(state.loadingMoreEntries.value).toBe(false)
    expect(state.entriesError.value).toBe('')
    expect(onStatus).not.toHaveBeenCalled()
    scope.stop()
  })

  it('reloads an unread result set after a batch mutation changes membership', async () => {
    const scope = effectScope()
    const state = scope.run(() => useRssEntries({
      selectedAccountId: ref(1),
      selectedFeedId: ref(null),
      feeds: ref([]),
      searchQuery: ref(''),
      searchTrigger: ref(0),
      getFeedTitle: () => '',
    }))!
    state.activeFilter.value = 'unread'
    await nextTick()
    await nextTick()
    vi.mocked(getRssEntries).mockClear()
    const entry = entryFixture()
    state.entries.value = [entry]
    state.totalEntries.value = 1
    state.contextMenuEntry.value = entry

    await state.batchUpdateReadStatus('all', true)

    expect(updateRssEntries).toHaveBeenCalledWith({ entryIds: [entry.id], isRead: true })
    expect(getRssEntries).toHaveBeenCalledWith(expect.objectContaining({ isRead: false, page: 1 }))
    expect(state.page.value).toBe(1)
    scope.stop()
  })

  it('reloads the starred result set after removing a star', async () => {
    const scope = effectScope()
    const state = scope.run(() => useRssEntries({
      selectedAccountId: ref(1),
      selectedFeedId: ref(null),
      feeds: ref([]),
      searchQuery: ref(''),
      searchTrigger: ref(0),
      getFeedTitle: () => '',
    }))!
    state.activeFilter.value = 'starred'
    await nextTick()
    await nextTick()
    vi.mocked(getRssEntries).mockClear()
    const entry = entryFixture({ is_starred: true })
    state.entries.value = [entry]

    await state.toggleStarStatus(entry)

    expect(updateRssEntry).toHaveBeenCalledWith(entry.id, { isStarred: false })
    expect(getRssEntries).toHaveBeenCalledWith(expect.objectContaining({ isStarred: true, page: 1 }))
    scope.stop()
  })
})

const entryFixture = (overrides: Partial<RssEntry> = {}): RssEntry => ({
  id: 1,
  account_id: 1,
  feed_id: 2,
  external_entry_id: 'entry-1',
  canonical_url: 'https://example.com/posts/1',
  title: 'Entry',
  summary: null,
  thumbnail: null,
  author: null,
  published_at: null,
  is_read: false,
  is_starred: false,
  ...overrides,
})
