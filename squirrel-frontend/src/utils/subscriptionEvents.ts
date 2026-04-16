export const SUBSCRIPTION_REMOVED_EVENT = 'subscription:removed'

export type SubscriptionRemovedDetail = {
  subscriptionId: string | number
}

export const notifySubscriptionRemoved = (subscriptionId: string | number) => {
  if (typeof window === 'undefined') return

  window.dispatchEvent(new CustomEvent<SubscriptionRemovedDetail>(SUBSCRIPTION_REMOVED_EVENT, {
    detail: { subscriptionId },
  }))
}

export const onSubscriptionRemoved = (
  handler: (detail: SubscriptionRemovedDetail) => void,
) => {
  if (typeof window === 'undefined') {
    return () => {}
  }

  const listener = (event: Event) => {
    const detail = (event as CustomEvent<SubscriptionRemovedDetail>).detail
    if (!detail?.subscriptionId) return
    handler(detail)
  }

  window.addEventListener(SUBSCRIPTION_REMOVED_EVENT, listener)
  return () => window.removeEventListener(SUBSCRIPTION_REMOVED_EVENT, listener)
}
