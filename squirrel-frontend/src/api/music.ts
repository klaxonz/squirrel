import { get, post } from '@/utils/request'

export type MusicTrack = {
  id: string
  title: string
  artist: string
  album: string
  hash: string
  album_id: string
  album_audio_id: string
  duration: number
  cover: string
}

export type MusicSearchResult = {
  items: MusicTrack[]
  page: number
  page_size: number
  total: number
}

export type MusicPlayUrl = {
  url: string
  quality: string
  expires_at?: string | null
  raw?: Record<string, unknown>
}

export type MusicLyricLine = {
  time: number
  text: string
}

export type MusicLyricResult = {
  lines: MusicLyricLine[]
  raw: string
}

export type MusicAuthStatus = {
  logged_in: boolean
  source: string
  userid: string
}

export type MusicQrLogin = {
  key: string
  url: string
  base64: string
}

export type MusicQrLoginStatus = {
  status: number
  logged_in: boolean
  auth: MusicAuthStatus
  raw: Record<string, unknown>
}

export const searchMusic = (params: {
  query: string
  page?: number
  page_size?: number
}) => {
  return get<MusicSearchResult>('/api/music/search', params)
}

export const getMusicPlayUrl = (params: {
  hash: string
  album_audio_id?: string
  quality?: string
}) => {
  return get<MusicPlayUrl>('/api/music/play-url', params)
}

export const getMusicLyric = (params: {
  title: string
  artist?: string
  hash: string
  album_audio_id?: string
  duration?: number
}) => {
  return get<MusicLyricResult>('/api/music/lyric', params)
}

export const getMusicAuthStatus = () => {
  return get<MusicAuthStatus>('/api/music/auth/status')
}

export const createMusicQrLogin = () => {
  return post<MusicQrLogin>('/api/music/auth/qr')
}

export const checkMusicQrLogin = (key: string) => {
  return get<MusicQrLoginStatus>('/api/music/auth/qr/check', { key })
}
