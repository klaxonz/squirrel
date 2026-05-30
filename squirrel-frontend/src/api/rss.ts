import { del as delRequest, get, post, put, patch } from '@/utils/request'

export type RssAccountPayload = {
  provider: string
  name: string
  base_url: string
  username?: string
  credential?: string
  enabled?: boolean
  sync_entry_limit?: number | null
}

export const getRssAccounts = async () => get('/api/rss/accounts')

export const createRssAccount = async (payload: RssAccountPayload) => post('/api/rss/accounts', payload)

export const updateRssAccount = async (accountId: string | number, payload: Partial<RssAccountPayload>) => {
  return put(`/api/rss/accounts/${accountId}`, payload)
}

export const deleteRssAccount = async (accountId: string | number) => delRequest(`/api/rss/accounts/${accountId}`)

export const testRssAccountConfig = async (payload: RssAccountPayload) => post('/api/rss/accounts/test', payload)

export const testRssAccount = async (accountId: string | number) => post(`/api/rss/accounts/${accountId}/test`)

export const syncRssAccount = async (accountId: string | number, entryLimit?: number, forceFullSync?: boolean) => {
  const params: Record<string, unknown> = {}
  if (entryLimit) params.entryLimit = entryLimit
  if (forceFullSync) params.forceFullSync = true
  return post(`/api/rss/accounts/${accountId}/sync/start`, null, { params })
}

export const getRssSyncStatus = async (accountId: string | number) => get(`/api/rss/accounts/${accountId}/sync/status`)

export const getRssFeeds = async (params: Record<string, unknown> = {}) => get('/api/rss/feeds', params)

export const getRssEntries = async (params: Record<string, unknown> = {}) => get('/api/rss/entries', params)

export const updateRssEntry = async (entryId: string | number, payload: { isRead?: boolean; isStarred?: boolean }) => {
  return patch(`/api/rss/entries/${entryId}`, payload)
}

export const updateRssEntries = async (payload: { entryIds: Array<string | number>; isRead: boolean }) => {
  return patch('/api/rss/entries/bulk', payload)
}
