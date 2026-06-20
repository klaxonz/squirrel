import type { SubscriptionListItem } from '@/features/video/types/subscription'

/**
 * Canonical subscription-list sort: special-followed channels first, then by
 * creation date descending (newest first).
 *
 * Extracted from Subscribed.vue's inline `sortChannels` so the "special-first,
 * then recency" rule is a single reusable pure function. Any surface that
 * renders an ordered subscription list (sidebar, grid, management view) should
 * apply the same ordering to stay consistent.
 *
 * Returns a new array (non-mutating) so callers can safely assign the result
 * to a ref without aliasing the input.
 */
export function sortSubscriptions(items: SubscriptionListItem[]): SubscriptionListItem[] {
  return [...items].sort((a, b) => {
    if (a.is_special_followed !== b.is_special_followed) {
      return a.is_special_followed ? -1 : 1
    }
    return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
  })
}
