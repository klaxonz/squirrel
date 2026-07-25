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

  it('opens original articles with the native in-app web view on desktop', async () => {
    const openInAppWebView = vi.fn().mockResolvedValue(true)
    const hideInAppWebView = vi.fn().mockResolvedValue(true)
    const openWebContent = vi.fn().mockResolvedValue(true)
    const openExternal = vi.fn().mockResolvedValue(true)
    vi.mocked(getDesktopBridge).mockReturnValue({
      isDesktop: true,
      openInAppWebView,
      hideInAppWebView,
      setInAppWebViewBounds: vi.fn().mockResolvedValue(true),
      reloadInAppWebView: vi.fn().mockResolvedValue(true),
      openWebContent,
      openExternal,
    } as never)

    const host = document.createElement('div')
    host.getBoundingClientRect = () => ({
      x: 40,
      y: 80,
      top: 80,
      left: 40,
      bottom: 680,
      right: 840,
      width: 800,
      height: 600,
      toJSON: () => ({}),
    })

    const state = useRssReader({})
    state.inAppWebViewHostRef.value = host
    state.readingEntry.value = {
      id: 1,
      account_id: 1,
      feed_id: 1,
      external_entry_id: 'entry-1',
      canonical_url: 'https://champhoon.xyz/log/hello-astro/',
      title: 'Post',
      summary: null,
      thumbnail: null,
      author: null,
      published_at: null,
      is_read: false,
      is_starred: false,
    }

    await expect(state.openInAppBrowser()).resolves.toBe(true)
    expect(state.showInAppBrowser.value).toBe(true)
    expect(openInAppWebView).toHaveBeenCalledWith({
      url: 'https://champhoon.xyz/log/hello-astro/',
      bounds: { x: 40, y: 80, width: 800, height: 600 },
    })
    expect(openWebContent).not.toHaveBeenCalled()
    expect(openExternal).not.toHaveBeenCalled()

    state.closeInAppBrowser()
    expect(state.showInAppBrowser.value).toBe(false)
    await Promise.resolve()
    expect(hideInAppWebView).toHaveBeenCalled()
  })

  it('uses iframe overlay when native in-app web view is unavailable', async () => {
    vi.mocked(getDesktopBridge).mockReturnValue({
      isDesktop: false,
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

    await expect(state.openInAppBrowser()).resolves.toBe(true)
    expect(state.showInAppBrowser.value).toBe(true)
    expect(state.usesNativeInAppWebView.value).toBe(false)
    expect(state.iframeLoadKey.value).toBe(1)
  })

  it('rejects non-HTTP article URLs before showing the overlay', async () => {
    const openInAppWebView = vi.fn()
    vi.mocked(getDesktopBridge).mockReturnValue({
      isDesktop: true,
      openInAppWebView,
    } as never)
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

    await expect(state.openInAppBrowser()).resolves.toBe(false)
    expect(state.showInAppBrowser.value).toBe(false)
    expect(openInAppWebView).not.toHaveBeenCalled()
    expect(onStatus).toHaveBeenCalledWith('文章链接无效', true)
  })

  it('rejects non-HTTP article URLs before showing the overlay', async () => {
    const probeFrameEmbeddability = vi.fn()
    vi.mocked(getDesktopBridge).mockReturnValue({
      isDesktop: true,
      probeFrameEmbeddability,
    } as never)
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

    await expect(state.openInAppBrowser()).resolves.toBe(false)
    expect(state.showInAppBrowser.value).toBe(false)
    expect(probeFrameEmbeddability).not.toHaveBeenCalled()
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
