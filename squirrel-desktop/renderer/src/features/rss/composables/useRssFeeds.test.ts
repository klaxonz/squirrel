import { beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, ref } from 'vue'
import { getRssFeeds, subscribeRssFeed } from '@/shared/api'
import { useRssFeeds } from './useRssFeeds'

vi.mock('@/shared/api', () => ({
  getRssFeeds: vi.fn().mockResolvedValue({ data: [] }),
  markRssFeedAsRead: vi.fn(),
  subscribeRssFeed: vi.fn(),
  syncRssFeed: vi.fn(),
  unsubscribeRssFeed: vi.fn(),
  updateRssFeed: vi.fn(),
}))

vi.mock('@/shared/composables/usePointerOutside', () => ({
  usePointerOutside: vi.fn(),
}))

describe('useRssFeeds', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getRssFeeds).mockResolvedValue({ data: [] })
  })

  it('stays in loading state until the initial feed request settles', async () => {
    type FeedsResponse = Awaited<ReturnType<typeof getRssFeeds>>
    let resolveRequest!: (value: FeedsResponse) => void
    vi.mocked(getRssFeeds).mockImplementationOnce(
      () => new Promise<FeedsResponse>((resolve) => {
        resolveRequest = resolve
      }),
    )

    const scope = effectScope()
    const state = scope.run(() => useRssFeeds({
      selectedAccountId: ref(1),
      canManageSubscriptions: ref(true),
    }))!

    expect(state.loadingFeeds.value).toBe(true)

    const loading = state.loadFeeds()
    expect(state.loadingFeeds.value).toBe(true)

    resolveRequest({ data: [] })
    await loading

    expect(state.loadingFeeds.value).toBe(false)
    scope.stop()
  })

  it('clears local feeds without issuing an unscoped request when no account is selected', async () => {
    const scope = effectScope()
    const state = scope.run(() => useRssFeeds({
      selectedAccountId: ref(null),
      canManageSubscriptions: ref(false),
    }))!
    state.feeds.value = [{
      id: 1,
      account_id: 1,
      external_feed_id: 'feed-1',
      title: 'Old feed',
      feed_url: null,
      site_url: null,
      icon_url: null,
      category: null,
      enabled: true,
      open_method: null,
      last_entry_sync_at: null,
    }]

    await state.loadFeeds()

    expect(getRssFeeds).not.toHaveBeenCalled()
    expect(state.feeds.value).toEqual([])
    expect(state.loadingFeeds.value).toBe(false)
    scope.stop()
  })

  it('does not call unsupported subscription APIs for providers such as Fever', async () => {
    const scope = effectScope()
    const state = scope.run(() => useRssFeeds({
      selectedAccountId: ref(1),
      canManageSubscriptions: ref(false),
    }))!
    state.subscribeForm.value.feedUrl = 'https://example.com/feed.xml'

    await state.handleSubscribeFeed()

    expect(subscribeRssFeed).not.toHaveBeenCalled()
    expect(state.subscribeError.value).toBe(true)
    expect(state.subscribeMessage.value).toContain('不支持')
    scope.stop()
  })
})
