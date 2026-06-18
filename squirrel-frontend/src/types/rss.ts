// DTOs for /api/rss/* — field shapes mirror the backend serializers.
// See backend: domains/rss/application/services/{account,library}/serialization.py
//
// Notes:
// - Datetimes here use .isoformat() ("2026-06-18T20:23:00"), unlike the
//   SerializerMixin "YYYY-MM-DD HH:MM:SS" used elsewhere — both are TS string.
// - credential_encrypted / is_deleted / raw_data / user_id are STRIPPED from
//   responses; never re-add credential fields to these types.

export interface RssAccount {
  id: number
  provider: string
  name: string
  base_url: string
  username: string | null
  enabled: boolean
  sync_entry_limit: number | null
  last_sync_at: string | null
  last_error: string | null
  created_at: string | null
  updated_at: string | null
}

export interface RssFeed {
  id: number
  account_id: number
  external_feed_id: string
  title: string
  feed_url: string | null
  site_url: string | null
  icon_url: string | null
  category: string | null
  enabled: boolean
  open_method: string | null
  last_entry_sync_at: string | null
}

export interface RssEntry {
  id: number
  account_id: number
  feed_id: number
  external_entry_id: string
  canonical_url: string
  title: string
  summary: string | null
  thumbnail: string | null
  author: string | null
  published_at: string | null
  is_read: boolean
  is_starred: boolean
}

/** GET /api/rss/entries/recently-viewed item. */
export interface RssEntryRecentlyViewed extends RssEntry {
  viewed_at: string
}

/** Wrapper for GET /api/rss/entries. */
export interface RssEntryListResponse {
  total: number
  page: number
  pageSize: number
  data: RssEntry[]
}

/** Wrapper for GET /api/rss/feeds and /api/rss/accounts. */
export interface RssListResponse<T> {
  data: T[]
}

/** syncRssFeed returns the count of newly synced entries. */
export interface RssFeedSyncResult {
  entries?: number
}
