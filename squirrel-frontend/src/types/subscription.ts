// DTOs for /api/subscription/* — field shapes mirror the backend response.
// See backend: domains/subscription/interfaces/http/basic.py +
//   domains/subscription/application/services/core/listing/serialization.py
//
// Notes:
// - List response: { total, page, pageSize, data: SubscriptionListItem[] }
// - Datetimes are "YYYY-MM-DD HH:MM:SS" strings (or "" if null).
// - Detail omits recent_videos + unread_count (those are list-only).

import type { VideoListItem } from './video'

export type SubscriptionType = 'CHANNEL' | 'PLAYLIST' | 'ACTRESS' | 'MOVIE' | 'TV_SERIES' | 'ACTOR' | string

/** Recent video embedded in subscription list items. */
export interface SubscriptionRecentVideo {
  id: number
  title: string
  url: string
  thumbnail: string | null
  duration: number
  publish_date: string | null
}

/** Item in GET /api/subscription/list `data[]`. */
export interface SubscriptionListItem {
  id: number
  type: SubscriptionType
  name: string
  url: string
  avatar: string | null
  description: string | null
  total_videos: number
  is_deleted: boolean
  extra_data: Record<string, unknown> | string | null
  created_at: string | null
  updated_at: string | null
  is_nsfw: boolean
  is_special_followed: boolean
  total_extract: number
  unread_count: number
  sync_status: string
  last_sync_at: string | null
  last_success_at: string | null
  next_sync_at: string | null
  last_error: string | null
  pending_video_count: number
  site: string | null
  recent_videos: SubscriptionRecentVideo[]
  // ponytail: SubscriptionCard reads latest_videos / last_published_at which
  // the traced serializer names recent_videos (and last_success_at). Kept as
  // optional aliases so the card keeps rendering if the backend emits either;
  // reconcile against the live payload before promoting to required.
  latest_videos?: SubscriptionRecentVideo[]
  last_published_at?: string | null
}

/** Wrapper for GET /api/subscription/list. */
export interface SubscriptionListResponse {
  total: number
  page: number
  pageSize: number
  data: SubscriptionListItem[]
}

/** GET /api/subscription/detail/{id}. */
export interface SubscriptionDetail {
  id: number
  type: SubscriptionType
  name: string
  url: string | null
  avatar: string | null
  description: string | null
  total_videos: number
  is_deleted: boolean
  extra_data: Record<string, unknown> | string | null
  created_at: string
  updated_at: string
  total_extract: number
  is_nsfw: boolean
  is_special_followed: boolean
  sync_status: string
  last_sync_at: string
  last_success_at: string
  next_sync_at: string
  last_error: string | null
  pending_video_count: number
  site: string | null
}

/** GET /api/subscription/options item. */
export interface SubscriptionOption {
  subscription_id: number
  subscription_name: string
  subscription_avatar: string | null
}

/** Result of subscribe/unsubscribe/status. */
export interface SubscriptionToggleResult {
  is_subscribed: boolean
  subscription_id: number | null
}

/** Re-export VideoListItem for modules that pair subscriptions with their videos. */
export type { VideoListItem }
