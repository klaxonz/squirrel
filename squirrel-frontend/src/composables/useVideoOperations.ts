import { getVideoUrlInfo } from '@/api'
import { Logger } from '@/utils/logger'
import type { MediaSource } from '@/components/video-player/core'

type VideoId = string | number

type VideoUrlOptions = {
  forceRefresh?: boolean
}

type ApiResult<T> = { data?: T | null; error?: any }

type VideoUrlInfo = {
  mpd_url?: string
  video_url?: string
  audio_url?: string
  qualities?: Array<{
    value: string
    label: string
    height?: number
    bandwidth?: number
    codec?: string
    id?: string | number
    index?: number
  }>
}

type DesktopWindow = Window & {
  desktopApp?: {
    isDesktop?: boolean
  }
}

const isDesktopPlaybackClient = () => {
  if (typeof window === 'undefined') return false

  const desktopWindow = window as DesktopWindow
  if (desktopWindow.desktopApp?.isDesktop === true) return true
  if (typeof navigator === 'undefined') return false

  const userAgent = String(navigator.userAgent || '')
  return /electron|tauri/i.test(userAgent)
}

export default function useVideoOperations() {
  const extractErrorCode = (msg: unknown) => {
    if (!msg || typeof msg !== 'string') return null
    const match = msg.match(/\(([^)]+)\)\s*$/)
    return match ? match[1] : null
  }

  const getPlaybackSource = async (videoId: VideoId, options: VideoUrlOptions = {}): Promise<MediaSource> => {
    const { forceRefresh = false } = options
    if (!videoId) throw Object.assign(new Error('无效的视频ID'), { code: 'BAD_REQUEST' })

    try {
      // 统一通过后端获取播放链接（VideoUrlDto），后端会在 bilibili/YouTube 情况下返回 mpd_url 与可选清晰度
      Logger.debug('[getPlaybackSource] Fetching /api/video/url', { videoId, forceRefresh })
      const clientType = isDesktopPlaybackClient() ? 'desktop' : undefined
      const { data, error } = (await getVideoUrlInfo(videoId, { forceRefresh, clientType })) as ApiResult<VideoUrlInfo>

      if (error) {
        const msg = error.data?.msg || error.message
        const errCode = extractErrorCode(msg) || error.data?.code || error.type || 'UNKNOWN'
        throw Object.assign(new Error(msg || '无法获取播放链接'), { code: errCode })
      }

      const mpdUrl = data?.mpd_url
      const videoUrl = data?.video_url
      const audioUrl = data?.audio_url
      const qualities = (data?.qualities || []).map((item) => ({
        id: item.id ?? item.value,
        label: item.label,
        height: item.height,
        bitrate: item.bandwidth,
        codec: item.codec
      }))
      const synthesizedMpdUrl = videoUrl && audioUrl && !mpdUrl
        ? `/api/video/mpd?video_id=${encodeURIComponent(String(videoId))}`
        : undefined

      const key = `${videoId}:${Date.now()}`
      const progressKey = String(videoId)
      const resolvedMpdUrl = mpdUrl || synthesizedMpdUrl

      if (resolvedMpdUrl) return { src: resolvedMpdUrl, type: 'auto', key, progressKey, qualities }

      if (!videoUrl && !audioUrl) {
        throw Object.assign(new Error('无法获取播放链接'), { code: 'NO_STREAM_URL' })
      }

      return {
        src: videoUrl || audioUrl || '',
        type: 'auto',
        key,
        progressKey,
        qualities
      }
    } catch (err) {
      throw err
    }
  }

  return {
    getPlaybackSource,
  }
}
