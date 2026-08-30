// @vitest-environment jsdom

import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { openExternalUrl } from '@/shared/lib/externalUrl'
import type { RssEntry } from '@/features/rss/types/rss'
import { useRssReaderWorkspace } from './useRssReaderWorkspace'

vi.mock('@/shared/lib/externalUrl', () => ({
  openExternalUrl: vi.fn().mockResolvedValue(true),
}))

const entry = (id: number): RssEntry => ({
  id,
  account_id: 1,
  feed_id: 1,
  external_entry_id: `entry-${id}`,
  canonical_url: `https://example.com/${id}`,
  title: `Entry ${id}`,
  excerpt: null,
  summary: null,
  thumbnail: null,
  author: null,
  published_at: null,
  is_read: false,
  is_starred: false,
})

describe('useRssReaderWorkspace', () => {
  it('opens external entries without switching to the reader pane', () => {
    const first = entry(1)
    const readingEntry = ref<RssEntry | null>(null)
    const showPane = vi.fn()
    const toggleReadStatus = vi.fn().mockResolvedValue(undefined)
    const recordRecentlyViewed = vi.fn()
    const state = useRssReaderWorkspace({
      reader: {
        readingEntry,
        showReaderSettings: ref(false),
        showInAppBrowser: ref(false),
        handleKeyDown: vi.fn(),
        closeInAppBrowser: vi.fn(),
        openInAppBrowser: vi.fn(),
      },
      filteredEntries: ref([first]),
      entriesContainer: ref(null),
      findFeedByEntry: vi.fn(() => ({ id: 1, open_method: 'external_browser' }) as never),
      toggleReadStatus,
      toggleStarStatus: vi.fn().mockResolvedValue(undefined),
      recordRecentlyViewed,
      onShowReaderPane: showPane,
    })

    state.openReader(first)

    expect(openExternalUrl).toHaveBeenCalledWith(first.canonical_url)
    expect(toggleReadStatus).toHaveBeenCalledWith(first, false)
    expect(recordRecentlyViewed).toHaveBeenCalledWith(first)
    expect(showPane).not.toHaveBeenCalled()
  })

  it('moves to the next filtered entry with keyboard navigation', () => {
    const first = entry(1)
    const second = entry(2)
    const readingEntry = ref<RssEntry | null>(first)
    const showPane = vi.fn()
    const state = useRssReaderWorkspace({
      reader: {
        readingEntry,
        showReaderSettings: ref(false),
        showInAppBrowser: ref(false),
        handleKeyDown: vi.fn(),
        closeInAppBrowser: vi.fn(),
        openInAppBrowser: vi.fn(),
      },
      filteredEntries: ref([first, second]),
      entriesContainer: ref(null),
      findFeedByEntry: vi.fn(() => undefined),
      toggleReadStatus: vi.fn().mockResolvedValue(undefined),
      toggleStarStatus: vi.fn().mockResolvedValue(undefined),
      recordRecentlyViewed: vi.fn(),
      onShowReaderPane: showPane,
    })
    const event = new KeyboardEvent('keydown', { key: 'ArrowDown', cancelable: true })
    state.handleWorkspaceKeyDown(event)

    expect(event.defaultPrevented).toBe(true)
    expect(readingEntry.value?.id).toBe(second.id)
    expect(showPane).toHaveBeenCalled()
  })
})
