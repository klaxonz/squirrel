export interface VideoClipMarker {
  id: number
  video_id: number
  title?: string
  note?: string
  preview_image_url?: string
  start_time: number
  end_time: number
  duration_seconds?: number
  created_at?: string
  updated_at?: string
}
