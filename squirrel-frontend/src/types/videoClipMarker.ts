export interface VideoClipMarker {
  id: number
  video_id: number
  title?: string | null
  note?: string | null
  preview_image_url?: string | null
  start_time: number
  end_time: number
  duration_seconds?: number
  created_at?: string | null
  updated_at?: string | null
}
