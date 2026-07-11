/** DTOs for /api/creator/* */

export interface CreatorDetail {
  id: number
  name: string | null
  url: string
  avatar: string | null
  description: string | null
  is_deleted?: boolean
  extra_data?: Record<string, unknown> | string | null
  created_at?: string | null
  updated_at?: string | null
  total_videos: number
}
