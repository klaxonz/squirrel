import { get, post, put, del } from '@/utils/request'

export const listPlaylists = async (params: Record<string, unknown> = {}) => {
  return get('/api/playlist', params)
}

export const getPlaylistDetail = async (playlistId: number | string) => {
  return get(`/api/playlist/${playlistId}`)
}

export const getPlaylistItems = async (playlistId: number | string) => {
  return get(`/api/playlist/${playlistId}/items`)
}

export const createPlaylist = async (data: {
  name: string
  description?: string | null
}) => {
  return post('/api/playlist', data)
}

export const updatePlaylist = async (
  playlistId: number | string,
  data: {
    name?: string | null
    description?: string | null
  }
) => {
  return put(`/api/playlist/${playlistId}`, data)
}

export const deletePlaylist = async (playlistId: number | string) => {
  return del(`/api/playlist/${playlistId}`)
}

export const addVideoToPlaylist = async (data: {
  video_id: number | string
  playlist_id?: number | string | null
}) => {
  return post('/api/playlist/items', data)
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
  return put('/api/playlist/items/reorder', data)
}

export const getDefaultPlaylist = async () => {
  return get('/api/playlist/default')
}

export const playNextVideo = async (
  playlistId: number | string,
  videoId: number | string
) => {
  return post(`/api/playlist/${playlistId}/play-next`, null, {
    params: { video_id: videoId },
  })
}
