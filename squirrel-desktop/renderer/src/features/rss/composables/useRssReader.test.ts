// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { getDesktopBridge } from '@/shared/composables/useDesktopBridge'
import { getRssEntry } from '@/shared/api'
import { useRssReader } from './useRssReader'

vi.mock('@/shared/composables/useDesktopBridge', () => ({
  getDesktopBridge: vi.fn(),
}))

vi.mock('@/shared/composables/usePointerOutside', () => ({
  usePointerOutside: vi.fn(),
}))

vi.mock('@/shared/api', () => ({
  getRssEntry: vi.fn(),
}))

describe('useRssReader', () => {
  beforeEach(() => {
    const values = new Map<string, string>()
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key),
      clear: () => values.clear(),
    })
    vi.clearAllMocks()
    vi.mocked(getRssEntry).mockResolvedValue({
      id: 1,
      account_id: 1,
      feed_id: 1,
      external_entry_id: 'entry-1',
      canonical_url: 'https://example.com/post',
      title: 'Post',
      excerpt: 'Preview',
      summary: '<p>Full body</p>',
      thumbnail: null,
      author: null,
      published_at: null,
      is_read: false,
      is_starred: false,
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('defaults to sans and clamps readable font sizes', () => {
    const state = useRssReader({})

    expect(state.readerFontFamily.value).toBe('sans')
    expect(state.readerFontSize.value).toBe(18)

    state.setReaderFontSize(100)
    expect(state.readerFontSize.value).toBe(24)
    expect(localStorage.getItem('rss_reader_font_size')).toBe('24')

    state.setReaderFontSize(10)
    expect(state.readerFontSize.value).toBe(14)
  })

  it('opens original articles in the in-app iframe overlay', () => {
    const openWebContent = vi.fn().mockResolvedValue(true)
    vi.mocked(getDesktopBridge).mockReturnValue({
      isDesktop: true,
      openWebContent,
    } as never)
    const state = useRssReader({})
    state.readingEntry.value = {
      id: 1,
      account_id: 1,
      feed_id: 1,
      external_entry_id: 'entry-1',
      canonical_url: 'https://example.com/post',
      title: 'Post',
      summary: null,
      thumbnail: null,
      author: null,
      published_at: null,
      is_read: false,
      is_starred: false,
    }

    expect(state.openInAppBrowser()).toBe(true)
    expect(state.showInAppBrowser.value).toBe(true)
    expect(state.originalArticleUrl.value).toBe('https://example.com/post')
    expect(state.iframeLoadKey.value).toBe(1)
    expect(openWebContent).not.toHaveBeenCalled()
  })

  it('rejects non-HTTP article URLs before showing the overlay', () => {
    const openWebContent = vi.fn().mockResolvedValue(true)
    vi.mocked(getDesktopBridge).mockReturnValue({ isDesktop: true, openWebContent } as never)
    const onStatus = vi.fn()
    const state = useRssReader({ onStatus })
    state.readingEntry.value = {
      id: 1,
      account_id: 1,
      feed_id: 1,
      external_entry_id: 'entry-1',
      canonical_url: 'javascript:alert(1)',
      title: 'Post',
      summary: null,
      thumbnail: null,
      author: null,
      published_at: null,
      is_read: false,
      is_starred: false,
    }

    expect(state.openInAppBrowser()).toBe(false)
    expect(state.showInAppBrowser.value).toBe(false)
    expect(openWebContent).not.toHaveBeenCalled()
    expect(onStatus).toHaveBeenCalledWith('文章链接无效', true)
  })

  it('lazy-loads full article HTML once when opening a list row', async () => {
    const state = useRssReader({})
    state.readingEntry.value = {
      id: 1,
      account_id: 1,
      feed_id: 1,
      external_entry_id: 'entry-1',
      canonical_url: 'https://example.com/post',
      title: 'Post',
      excerpt: 'Preview',
      summary: null,
      thumbnail: null,
      author: null,
      published_at: null,
      is_read: false,
      is_starred: false,
    }

    await vi.waitFor(() => {
      expect(getRssEntry).toHaveBeenCalledTimes(1)
      expect(state.sanitizedArticleHtml.value).toContain('Full body')
      expect(state.loadingArticleContent.value).toBe(false)
    })
  })
})
