import { beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, ref } from 'vue'
import { getRssFeeds } from '@/shared/api'
import { useRssFeeds } from './useRssFeeds'

vi.mock('@/shared/api', () => ({
  getRssFeeds: vi.fn().mockResolvedValue({ data: [] }),
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
    vi.mocked(getRssFeeds).mockReset()
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
    }))!

    expect(state.loadingFeeds.value).toBe(true)

    const loading = state.loadFeeds()
    expect(state.loadingFeeds.value).toBe(true)

    resolveRequest({ data: [] })
    await loading

    expect(state.loadingFeeds.value).toBe(false)
    scope.stop()
  })
})
