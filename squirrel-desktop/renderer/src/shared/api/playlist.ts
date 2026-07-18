import { get, post, put, del } from '@/shared/lib/request'
import type { Playlist, PlaylistDetail, PlaylistItem } from '@/features/video/types/playlist'

// FastAPI defines the collection route with a trailing slash. Using the
// slashless form makes the Vite proxy follow a 307 to the backend origin,
// where the renderer-origin authentication cookie is no longer available.
const PLAYLIST_COLLECTION_PATH = '/api/playlist/'

export const listPlaylists = async (params: Record<string, unknown> = {}) => {
  return get<Playlist[]>(PLAYLIST_COLLECTION_PATH, params)
}

export const getPlaylistDetail = async (playlistId: number | string) => {
  return get<PlaylistDetail>(`/api/playlist/${playlistId}`)
}

export const getPlaylistItems = async (playlistId: number | string) => {
  return get<PlaylistItem[]>(`/api/playlist/${playlistId}/items`)
}

export const createPlaylist = async (data: {
  name: string
  description?: string | null
}) => {
  return post<Playlist>(PLAYLIST_COLLECTION_PATH, data)
}

export const updatePlaylist = async (
  playlistId: number | string,
  data: {
    name?: string | null
    description?: string | null
  }
) => {
  return put<Playlist>(`/api/playlist/${playlistId}`, data)
}

export const deletePlaylist = async (playlistId: number | string) => {
  return del(`/api/playlist/${playlistId}`)
}

export const addVideoToPlaylist = async (data: {
  video_id: number | string
  playlist_id?: number | string | null
}) => {
  return post<PlaylistItem>('/api/playlist/items', data)
}

export const removeVideoFromPlaylist = async (
  playlistId: number | string,
  videoId: number | string
) => {
  return del(`/api/playlist/${playlistId}/items/${videoId}`)
}

export const reorderPlaylistItem = async (data: {
  playlist_id: number | string
  video_id: number | string
  new_position: number
}) => {
  return put<PlaylistItem>('/api/playlist/items/reorder', data)
}

export const getDefaultPlaylist = async () => {
  return get<Playlist>('/api/playlist/default')
}

export const playNextVideo = async (
  playlistId: number | string,
  videoId: number | string
) => {
  return post(`/api/playlist/${playlistId}/play-next`, null, {
    params: { video_id: videoId },
  })
}
