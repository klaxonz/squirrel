import type { SubscriptionListItem } from '@/shared/types/subscription'

/** Sync statuses that should surface as operational failure on the desk. */
export function isSubscriptionSyncFailed(item: Pick<SubscriptionListItem, 'sync_status' | 'last_error'>): boolean {
  return item.sync_status === 'failed' || Boolean(item.last_error)
}

export function isSubscriptionSyncBusy(item: Pick<SubscriptionListItem, 'sync_status'>): boolean {
  return item.sync_status === 'queued' || item.sync_status === 'running'
}

export function formatUnreadCount(count: number): string {
  if (!Number.isFinite(count) || count <= 0) return ''
  if (count > 99) return '99+'
  return String(count)
}

export function subscriptionSyncErrorLabel(item: Pick<SubscriptionListItem, 'last_error' | 'sync_status'>): string {
  if (item.last_error?.trim()) return item.last_error.trim()
  if (item.sync_status === 'failed') return '同步失败'
  return ''
}
