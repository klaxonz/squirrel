import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { useRssEntries } from './useRssEntries'

vi.mock('@/shared/api', () => ({
  getRssEntries: vi.fn().mockResolvedValue({ data: [], total: 0 }),
  getRssRecentlyViewed: vi.fn().mockResolvedValue({ data: [] }),
  recordRssEntryView: vi.fn(),
  updateRssEntries: vi.fn(),
  updateRssEntry: vi.fn(),
}))

describe('useRssEntries', () => {
  it('defaults to the all entries filter', () => {
    const { activeFilter } = useRssEntries({
      selectedAccountId: ref(null),
      selectedFeedId: ref(null),
      feeds: ref([]),
      getFeedTitle: () => '',
    })

    expect(activeFilter.value).toBe('all')
  })
})
