import { del as delRequest, get, post, put } from '@/utils/request'

export type RssAccountPayload = {
  provider: string
  name: string
  base_url: string
  username?: string
  credential?: string
  enabled?: boolean
}

export const getRssAccounts = async () => get('/api/rss/accounts')

export const createRssAccount = async (payload: RssAccountPayload) => post('/api/rss/accounts', payload)

export const updateRssAccount = async (accountId: string | number, payload: Partial<RssAccountPayload>) => {
  return put(`/api/rss/accounts/${accountId}`, payload)
}

export const deleteRssAccount = async (accountId: string | number) => delRequest(`/api/rss/accounts/${accountId}`)

export const testRssAccountConfig = async (payload: RssAccountPayload) => post('/api/rss/accounts/test', payload)

export const testRssAccount = async (accountId: string | number) => post(`/api/rss/accounts/${accountId}/test`)

export const syncRssAccount = async (accountId: string | number, entryLimit = 50) => {
  return post(`/api/rss/accounts/${accountId}/sync`, null, { params: { entryLimit } })
}

export const getRssFeeds = async (params: Record<string, unknown> = {}) => get('/api/rss/feeds', params)

export const getRssEntries = async (params: Record<string, unknown> = {}) => get('/api/rss/entries', params)
