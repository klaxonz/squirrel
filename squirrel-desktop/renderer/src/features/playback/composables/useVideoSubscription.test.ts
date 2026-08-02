// @vitest-environment jsdom
import { createApp, defineComponent, nextTick, ref } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useVideoSubscription } from './useVideoSubscription'
import type { VideoPageVideo } from '@/features/playback/types/videoPlayback'

const api = vi.hoisted(() => ({
  getSubscriptionStatus: vi.fn(),
  subscribe: vi.fn(),
  unsubscribe: vi.fn(),
}))

vi.mock('@/shared/api', () => api)

type Deferred<T> = {
  promise: Promise<T>
  resolve: (value: T) => void
}

const deferred = <T>(): Deferred<T> => {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { promise, resolve }
}

const flushPromises = () => new Promise<void>((resolve) => setTimeout(resolve, 0))

const mountSubscription = (video = ref<VideoPageVideo | null>({
  id: 1,
  title: '测试视频',
  subscriptions: [{ id: 1, name: '频道', url: 'https://example.com/channel' }],
})) => {
  let subscription!: ReturnType<typeof useVideoSubscription>
  const app = createApp(defineComponent({
    setup() {
      subscription = useVideoSubscription({ video })
      return () => null
    },
  }))
  const host = document.createElement('div')
  document.body.append(host)
  app.mount(host)
  return { app, video, subscription }
}

describe('useVideoSubscription', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    document.body.replaceChildren()
  })

  it('exposes a status error and clears it after a successful retry', async () => {
    api.getSubscriptionStatus
      .mockRejectedValueOnce(new Error('network unavailable'))
      .mockResolvedValueOnce({ is_subscribed: true, subscription_id: 12 })

    const { app, subscription } = mountSubscription()
    await flushPromises()

    expect(subscription.subscriptionStatusError.value).toContain('network unavailable')
    expect(subscription.isSubscriptionChecked.value).toBe(false)

    await expect(subscription.refreshSubscriptionStatus()).resolves.toEqual({ ok: true })
    expect(subscription.subscriptionStatusError.value).toBeNull()
    expect(subscription.isSubscriptionChecked.value).toBe(true)
    expect(subscription.isSubscribed.value).toBe(true)
    app.unmount()
  })

  it('keeps the current state and reports a failed toggle', async () => {
    api.getSubscriptionStatus.mockResolvedValue({ is_subscribed: false, subscription_id: null })
    api.subscribe.mockRejectedValue(new Error('subscribe unavailable'))

    const { app, subscription } = mountSubscription()
    await flushPromises()

    await expect(subscription.handleSubscribe()).resolves.toEqual({
      ok: false,
      error: 'subscribe unavailable',
    })
    expect(subscription.subscriptionToggleError.value).toBe('subscribe unavailable')
    expect(subscription.isSubscribed.value).toBe(false)
    app.unmount()
  })

  it('ignores an old status response after the video changes', async () => {
    const first = deferred<{ is_subscribed: boolean; subscription_id: number }>()
    api.getSubscriptionStatus
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce({ is_subscribed: false, subscription_id: 22 })

    const { app, video, subscription } = mountSubscription()
    video.value = {
      id: 2,
      title: '新视频',
      subscriptions: [{ id: 2, name: '新频道', url: 'https://example.com/new-channel' }],
    }
    await nextTick()
    await flushPromises()

    first.resolve({ is_subscribed: true, subscription_id: 11 })
    await flushPromises()

    expect(subscription.primarySubscriptionUrl.value).toBe('https://example.com/new-channel')
    expect(subscription.isSubscriptionChecked.value).toBe(true)
    expect(subscription.isSubscribed.value).toBe(false)
    app.unmount()
  })
})
