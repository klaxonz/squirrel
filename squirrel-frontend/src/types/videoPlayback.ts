export type VideoId = string | number

export type InteractionType = string | number

export type VideoProfile = {
  id: VideoId
  name: string
  url?: string
  avatar?: string
  total_videos?: number
  is_nsfw?: boolean
}

export type ClipMarker = {
  id: VideoId
  title?: string
  start_time: number
  end_time: number
  duration_seconds?: number
  preview_image_url?: string
}

export type VideoSubtitle = {
  id: string
  label?: string
  language: string
  url?: string
  content?: string
  default?: boolean
}

export type VideoPageVideo = {
  id: VideoId
  title: string
  url?: string
  thumbnail?: string
  duration?: number
  publish_date?: string
  uploaded_at?: string
  description?: string
  source?: string
  site?: string
  interaction_type?: InteractionType
  last_position?: number
  clip_markers?: ClipMarker[]
  subtitles?: VideoSubtitle[]
  actors?: VideoProfile[]
  subscriptions?: VideoProfile[]
  uploader?: string
  uploader_name?: string
}

export type { ApiResult } from '@/types/api'
