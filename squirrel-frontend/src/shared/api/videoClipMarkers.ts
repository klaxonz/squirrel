import { del, get, post, put } from '@/shared/lib/request'
import type { VideoClipMarker } from '@/features/video/types/videoClipMarker'

export type VideoClipMarkerPayload = {
  video_id: string | number
  title?: string
  note?: string
  start_time: number
  end_time?: number
}

export type VideoClipMarkerUpdatePayload = {
  title?: string | null
  note?: string | null
  start_time?: number
  end_time?: number
}

export type VideoClipMarkerPreviewUploadPayload = {
  image_data_url: string
}

export const getVideoClipMarkers = async (videoId: string | number) => {
  return get<VideoClipMarker[]>('/api/video-clip-markers', { video_id: videoId })
}

export const createVideoClipMarker = async (payload: VideoClipMarkerPayload) => {
  return post<VideoClipMarker>('/api/video-clip-markers', payload)
}

export const updateVideoClipMarker = async (markerId: string | number, payload: VideoClipMarkerUpdatePayload) => {
  return put<VideoClipMarker>(`/api/video-clip-markers/${markerId}`, payload)
}

export const uploadVideoClipMarkerPreview = async (
  markerId: string | number,
  payload: VideoClipMarkerPreviewUploadPayload,
) => {
  return post<VideoClipMarker>(`/api/video-clip-markers/${markerId}/preview`, payload)
}

export const deleteVideoClipMarker = async (markerId: string | number) => {
  return del(`/api/video-clip-markers/${markerId}`)
}
