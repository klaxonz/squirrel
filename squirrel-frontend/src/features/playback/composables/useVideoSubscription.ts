import { computed, ref, watch, type ComputedRef, type Ref } from 'vue'
import { getSubscriptionStatus, subscribe, unsubscribe } from '@/shared/api'
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
  subscriptionButtonText: ComputedRef<string>
  handleSubscribe: () => Promise<void>
}

export function useVideoSubscription(options: UseVideoSubscriptionOptions): UseVideoSubscriptionReturn {
  const { video } = options

  const isCheckingSubscription = ref(false)
  const isSubscriptionChecked = ref(false)
  const isSubscribed = ref(false)
  const isSubscribing = ref(false)
  const subscriptionId = ref<number | null>(null)

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

  const refreshSubscriptionStatus = async (url: string) => {
    isSubscribed.value = false
    isSubscriptionChecked.value = false
    subscriptionId.value = null
    if (!url) return

    isCheckingSubscription.value = true
    try {
      const data = await getSubscriptionStatus(url)
      // Guard against a stale response if the primary URL changed mid-flight.
      if (url !== primarySubscriptionUrl.value) return
      isSubscribed.value = data?.is_subscribed === true
      subscriptionId.value = data?.subscription_id ?? null
      isSubscriptionChecked.value = true
    } catch {
      if (url !== primarySubscriptionUrl.value) return
      // silent — subscription status check failure just leaves it unchecked
    } finally {
      isCheckingSubscription.value = false
    }
  }

  watch(primarySubscriptionUrl, async (url) => {
    await refreshSubscriptionStatus(url)
  }, { immediate: true })

  const handleSubscribe = async () => {
    const url = primarySubscriptionUrl.value
    if (!url || isSubscribing.value) return

    isSubscribing.value = true
    try {
      const data = isSubscribed.value && subscriptionId.value
        ? await unsubscribe(subscriptionId.value)
        : await subscribe(url)

      // Optimistic update only on a fresh subscribe (unsubscribe is re-queried
      // below via refreshSubscriptionStatus, which is the source of truth).
      if (!isSubscribed.value) {
        isSubscribed.value = data?.is_subscribed === true
        subscriptionId.value = data?.subscription_id ?? null
        isSubscriptionChecked.value = true
      }

      await refreshSubscriptionStatus(url)
    } catch {
      // silent — a failed subscribe/unsubscribe leaves the toggle unchanged
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
    subscriptionButtonText,
    handleSubscribe,
  }
}
