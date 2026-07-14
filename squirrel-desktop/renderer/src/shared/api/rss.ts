import { del as delRequest, get, post, put, patch } from '@/shared/lib/request'
import type {
  RssAccount,
  RssFeed,
  RssEntry,
  RssEntryRecentlyViewed,
  RssEntryListResponse,
  RssListResponse,
  RssFeedSyncResult,
  RssSyncStatus,
  RssBulkUpdateResult,
  RssMutationResult,
  RssSyncStartResult,
  RssAccountTestResult,
} from '@/features/rss/types/rss'

export type RssAccountPayload = {
  provider: string
  name: string
  base_url: string
  username?: string
  credential?: string
  enabled?: boolean
  sync_entry_limit?: number | null
}

export const getRssAccounts = async () => get<RssListResponse<RssAccount>>('/api/rss/accounts')

export const createRssAccount = async (payload: RssAccountPayload) => post<RssAccount>('/api/rss/accounts', payload)

export const updateRssAccount = async (accountId: string | number, payload: Partial<RssAccountPayload>) => {
  return put<RssAccount>(`/api/rss/accounts/${accountId}`, payload)
}

export const deleteRssAccount = async (accountId: string | number) => delRequest(`/api/rss/accounts/${accountId}`)

export const testRssAccountConfig = async (payload: RssAccountPayload) => post<RssAccountTestResult>('/api/rss/accounts/test', payload)

export const testRssAccount = async (accountId: string | number) => post<RssAccountTestResult>(`/api/rss/accounts/${accountId}/test`)

export const syncRssAccount = async (accountId: string | number, entryLimit?: number, forceFullSync?: boolean) => {
  const params: Record<string, unknown> = {}
  if (entryLimit) params.entryLimit = entryLimit
  if (forceFullSync) params.forceFullSync = true
  return post<RssSyncStartResult>(`/api/rss/accounts/${accountId}/sync/start`, null, { params })
}

export const getRssSyncStatus = async (accountId: string | number) => get<RssSyncStatus>(`/api/rss/accounts/${accountId}/sync/status`)

export const getRssFeeds = async (params: Record<string, unknown> = {}) =>
  get<RssListResponse<RssFeed>>('/api/rss/feeds', params)

export const getRssEntries = async (params: Record<string, unknown> = {}) =>
  get<RssEntryListResponse>('/api/rss/entries', params)

export const updateRssEntry = async (entryId: string | number, payload: { isRead?: boolean; isStarred?: boolean }) => {
  return patch<RssEntry>(`/api/rss/entries/${entryId}`, payload)
}

export const updateRssEntries = async (payload: { entryIds: Array<string | number>; isRead: boolean }) => {
  return patch<RssBulkUpdateResult>('/api/rss/entries/bulk', payload)
}

export const recordRssEntryView = async (entryId: string | number) => {
  return post<RssMutationResult>(`/api/rss/entries/${entryId}/view`)
}

export const getRssRecentlyViewed = async () =>
  get<{ data: RssEntryRecentlyViewed[] }>('/api/rss/entries/recently-viewed')

export const subscribeRssFeed = async (payload: { accountId: number; feedUrl: string; category?: string }) => {
  return post<RssMutationResult>('/api/rss/feeds/subscribe', payload)
}

export const unsubscribeRssFeed = async (feedId: number, accountId: number) => {
  return delRequest<RssMutationResult>(`/api/rss/feeds/${feedId}`, null, { params: { accountId } })
}

export const syncRssFeed = async (feedId: number, entryLimit = 50) => {
  return post<RssFeedSyncResult>(`/api/rss/feeds/${feedId}/sync`, null, { params: { entryLimit } })
}

export const updateRssFeed = async (feedId: number, payload: Record<string, unknown>) => {
  return patch<RssMutationResult>(`/api/rss/feeds/${feedId}`, payload)
}

export const markRssFeedAsRead = async (feedId: number) => {
  return post<RssMutationResult>(`/api/rss/feeds/${feedId}/read`)
}
