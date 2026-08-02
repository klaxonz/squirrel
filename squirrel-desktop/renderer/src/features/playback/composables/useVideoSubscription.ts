import { computed, ref, watch, type ComputedRef, type Ref } from 'vue'
import { getSubscriptionStatus, subscribe, unsubscribe } from '@/shared/api'
import { errorMessage } from '@/shared/lib/errorMessage'
import type { VideoPageVideo, VideoProfile } from '@/features/playback/types/videoPlayback'

/**
 * Subscription status + toggle for the video play view.
 *
 * Owns the subscribe/unsubscribe state machine for the video's primary
 * subscription (the first subscription or, failing that, the first actor):
 * the per-URL status check, the optimistic toggle, the button label, and the
 * immediate watcher that re-checks status when the primary subscription URL
 * changes (video swap). Extracted from VideoPlay.vue so the toggle's
 * idempotency guards + the URL-staleness check live in one place.
 *
 * `primarySubscription` / `primarySubscriptionUrl` are returned because the view
 * also renders the avatar and uses the primary to de-duplicate the actor list —
 * those are projections of `video`, not subscription-only state.
 */
export interface UseVideoSubscriptionOptions {
  video: ComputedRef<VideoPageVideo | null> | Ref<VideoPageVideo | null>
}

export interface UseVideoSubscriptionReturn {
  primarySubscription: ComputedRef<VideoProfile | null>
  primarySubscriptionUrl: ComputedRef<string>
  isCheckingSubscription: Ref<boolean>
  isSubscribing: Ref<boolean>
  isSubscribed: Ref<boolean>
  isSubscriptionChecked: Ref<boolean>
  subscriptionStatusError: Ref<string | null>
  subscriptionToggleError: Ref<string | null>
  subscriptionButtonText: ComputedRef<string>
  refreshSubscriptionStatus: () => Promise<SubscriptionOperationResult>
  handleSubscribe: () => Promise<SubscriptionOperationResult>
}

export type SubscriptionOperationResult =
  | { ok: true }
  | { ok: false; error: string }

export function useVideoSubscription(options: UseVideoSubscriptionOptions): UseVideoSubscriptionReturn {
  const { video } = options

  const isCheckingSubscription = ref(false)
  const isSubscriptionChecked = ref(false)
  const isSubscribed = ref(false)
  const isSubscribing = ref(false)
  const subscriptionId = ref<number | null>(null)
  const subscriptionStatusError = ref<string | null>(null)
  const subscriptionToggleError = ref<string | null>(null)

  const primarySubscription = computed<VideoProfile | null>(() => {
    const v = video.value
    if (!v) return null
    return v.subscriptions?.[0] || v.actors?.[0] || null
  })

  const primarySubscriptionUrl = computed(() => String(primarySubscription.value?.url || '').trim())

  const subscriptionButtonText = computed(() => {
    if (isCheckingSubscription.value) return '检查中'
    if (isSubscribing.value) return '订阅中'
    return isSubscriptionChecked.value && isSubscribed.value ? '取消订阅' : '订阅'
  })

  const refreshSubscriptionStatusForUrl = async (url: string): Promise<SubscriptionOperationResult> => {
    isSubscribed.value = false
    isSubscriptionChecked.value = false
    subscriptionId.value = null
    subscriptionStatusError.value = null
    if (!url) return { ok: true }

    isCheckingSubscription.value = true
    try {
      const data = await getSubscriptionStatus(url)
      // Guard against a stale response if the primary URL changed mid-flight.
      if (url !== primarySubscriptionUrl.value) return { ok: true }
      isSubscribed.value = data?.is_subscribed === true
      subscriptionId.value = data?.subscription_id ?? null
      isSubscriptionChecked.value = true
      return { ok: true }
    } catch (error) {
      if (url !== primarySubscriptionUrl.value) return { ok: true }
      const message = errorMessage(error, '订阅状态检查失败，请重试')
      subscriptionStatusError.value = message
      return { ok: false, error: message }
    } finally {
      if (url === primarySubscriptionUrl.value) isCheckingSubscription.value = false
    }
  }

  const refreshSubscriptionStatus = () => refreshSubscriptionStatusForUrl(primarySubscriptionUrl.value)

  watch(primarySubscriptionUrl, async (url) => {
    subscriptionToggleError.value = null
    await refreshSubscriptionStatusForUrl(url)
  }, { immediate: true })

  const handleSubscribe = async (): Promise<SubscriptionOperationResult> => {
    const url = primarySubscriptionUrl.value
    if (!url) return { ok: false, error: '缺少可订阅的频道地址' }
    if (isSubscribing.value) return { ok: false, error: '订阅操作正在进行' }

    isSubscribing.value = true
    subscriptionToggleError.value = null
    try {
      const wasSubscribed = isSubscribed.value
      const data = wasSubscribed && subscriptionId.value
        ? await unsubscribe(subscriptionId.value)
        : await subscribe(url)

      if (!wasSubscribed) {
        isSubscribed.value = data?.is_subscribed === true
        subscriptionId.value = data?.subscription_id ?? null
        isSubscriptionChecked.value = true
      }

      const refreshResult = await refreshSubscriptionStatusForUrl(url)
      if (!refreshResult.ok) return refreshResult
      return { ok: true }
    } catch (error) {
      const message = errorMessage(error, isSubscribed.value ? '取消订阅失败，请重试' : '订阅失败，请重试')
      subscriptionToggleError.value = message
      return { ok: false, error: message }
    } finally {
      isSubscribing.value = false
    }
  }

  return {
    primarySubscription,
    primarySubscriptionUrl,
    isCheckingSubscription,
    isSubscribing,
    isSubscribed,
    isSubscriptionChecked,
    subscriptionStatusError,
    subscriptionToggleError,
    subscriptionButtonText,
    refreshSubscriptionStatus,
    handleSubscribe,
  }
}
