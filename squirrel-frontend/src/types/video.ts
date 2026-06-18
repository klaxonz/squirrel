// DTOs for /api/video/* — field shapes mirror the backend response exactly.
// See backend: domains/video/application/services/listing/{page_loader,detail_loader}.py
//
// Key facts from backend tracing:
// - List response uses `data` only (no `items` key).
// - List items do NOT carry is_read/is_liked/is_later — read/like state is
//   only derivable from last_position (list) and interaction_type + last_position
//   (detail). Frontend code reading those fields on list items was reading undefined.
// - subscriptions[]/actors[] are unions (PG profile ∪ extra-data profile); only
//   id/name/url are guaranteed, the rest optional.

import type { ClipMarker, VideoSubtitle } from './videoPlayback'

/** Profile merged from PG + extra-data; only id/name/url always present. */
export interface VideoProfile {
  id: number | string | null
  name: string
  url: string
  type?: string | null
  avatar?: string | null
  is_nsfw?: boolean | null
  is_special_followed?: boolean | null
  description?: string | null
  site?: string | null
}

/** Lighter shape returned by each item in GET /api/video/list `data[]`. */
export interface VideoListItem {
  id: number
  title: string
  url: string
  thumbnail: string | null
  duration: number | null
  last_position: number
  uploaded_at: string | null
  created_at: string
  subscriptions: VideoProfile[]
  actors: VideoProfile[]
  // ponytail: the list endpoint does NOT return site/description, but several
  // feed components read them defensively. Kept optional so those reads type
  // check; they resolve to undefined on list items and only populate on detail.
  site?: string | null
  description?: string | null
}

/** Wrapper for GET /api/video/list. */
export interface VideoListResponse {
  data: VideoListItem[]
  next_cursor: string | null
  has_more: boolean
}

/** Full shape returned by GET /api/video/detail (Video.to_dict + enriched keys). */
export interface VideoDetail {
  id: number
  title: string
  url: string
  domain: string | null
  description: string | null
  duration: number | null
  thumbnail: string | null
  publish_date: string | null
  is_deleted: boolean
  extra_data: Record<string, unknown> | null
  created_at: string
  updated_at: string
  // enriched by detail_loader
  interaction_type: number | null
  last_position: number
  subscriptions: VideoProfile[]
  actors: VideoProfile[]
  creators: VideoProfile[]
  clip_markers: ClipMarker[]
  subtitles?: VideoSubtitle[]
}

/** GET /api/video/random returns a bare video id reference. */
export interface RandomVideoResult {
  id: string | number
}

/** Flat history entry in GET /api/video-history/list `items[]`.
 *  Note: `id` is the video id; `history_id` is the history row id. */
export interface VideoHistoryEntry {
  id: number
  history_id: number
  title: string
  url: string
  thumbnail: string
  duration: number
  last_position: number
  played_at: string | null
  uploaded_at: string | null
  created_at: string | null
  subscriptions: VideoProfile[]
  actors: VideoProfile[]
  site: string | null
}

/** Wrapper for GET /api/video-history/list. */
export interface VideoHistoryListResponse {
  items: VideoHistoryEntry[]
  total: number
  page: number
  page_size: number
}
