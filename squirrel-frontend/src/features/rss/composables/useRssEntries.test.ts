import { beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, ref } from 'vue'
import { getRssEntries } from '@/shared/api'
import { useRssEntries } from './useRssEntries'

vi.mock('@/shared/api', () => ({
  getRssEntries: vi.fn().mockResolvedValue({ data: [], total: 0 }),
  getRssRecentlyViewed: vi.fn().mockResolvedValue({ data: [] }),
  recordRssEntryView: vi.fn(),
  updateRssEntries: vi.fn(),
  updateRssEntry: vi.fn(),
}))

describe('useRssEntries', () => {
  beforeEach(() => {
    vi.mocked(getRssEntries).mockClear()
  })

  it('defaults to the all entries filter', () => {
    const scope = effectScope()
    const { activeFilter } = scope.run(() => useRssEntries({
      selectedAccountId: ref(null),
      selectedFeedId: ref(null),
      feeds: ref([]),
      searchQuery: ref(''),
      searchTrigger: ref(0),
      getFeedTitle: () => '',
    }))!

    expect(activeFilter.value).toBe('all')
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
})
