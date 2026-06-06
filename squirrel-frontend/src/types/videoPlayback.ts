export type VideoId = string | number

export type InteractionType = string | number | null

export type VideoProfile = {
  id?: VideoId | null
  name?: string | null
  url?: string | null
  avatar?: string | null
  total_videos?: number | null
  is_nsfw?: boolean | null
}

export type ClipMarker = {
  id?: VideoId
  title?: string | null
  start_time: number
  end_time: number
  duration_seconds?: number | null
  preview_image_url?: string | null
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
  id?: VideoId
  title?: string | null
  url?: string | null
  thumbnail?: string | null
  duration?: number | null
  publish_date?: string | null
  uploaded_at?: string | null
  description?: string | null
  source?: string | null
  site?: string | null
  interaction_type?: InteractionType
  last_position?: number | null
  clip_markers?: ClipMarker[]
  subtitles?: VideoSubtitle[]
  actors?: VideoProfile[]
  subscriptions?: VideoProfile[]
  uploader?: string | null
  uploader_name?: string | null
}

export type ApiResult<T> = {
  data?: T | null
  error?: unknown | null
}
