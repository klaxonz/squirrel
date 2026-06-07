export type { ApiResult } from '@/types/api'

export type RssAccount = {
  id: number
  provider: string
  name: string
  base_url: string
  username?: string | null
  enabled: boolean
  last_sync_at?: string | null
  last_error?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export type RssFeed = {
  id: number
  account_id: number
  title: string
  feed_url?: string | null
  site_url?: string | null
  icon_url?: string | null
  category?: string | null
  open_method?: string | null
}

export type RssEntry = {
  id: number
  account_id: number
  feed_id: number
  external_entry_id: string
  canonical_url: string
  title: string
  summary?: string | null
  thumbnail?: string | null
  author?: string | null
  published_at?: string | null
  is_read: boolean
  is_starred: boolean
}

export type RecentEntry = RssEntry & {
  viewed_at: string
}

export type ReadBatchMode = 'above' | 'below' | 'all'
