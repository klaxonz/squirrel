export interface PlaylistItem {
  id: number
  playlist_id: number
  video_id: number
  position: number
  added_at: string
  video?: VideoBasic
}

export interface Playlist {
  id: number
  user_id: number
  name: string
  description: string | null
  is_default: boolean
  video_count: number
  created_at: string
  updated_at: string
}

export interface PlaylistDetail extends Playlist {
  items: PlaylistItem[]
}

export interface VideoBasic {
  id: number
  title: string
  url: string
  thumbnail?: string
  duration?: number
  publish_date?: string
  site?: string
  subscriptions?: SubscriptionBasic[]
}

export interface SubscriptionBasic {
  id: number
  name: string
  avatar?: string
  total_videos?: number
}

export type PlaylistId = number | string

export type VideoId = number | string
