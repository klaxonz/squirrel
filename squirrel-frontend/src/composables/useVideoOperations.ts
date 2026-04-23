import { getVideoUrlInfo } from '@/api'
import { Logger } from '@/utils/logger'
import type { MediaSource } from '@/components/video-player/core'

type VideoId = string | number

type VideoUrlOptions = {
  forceRefresh?: boolean
}

type PlaybackVideoLike = {
  url?: string | null
}

type ApiResult<T> = { data?: T | null; error?: any }

type VideoUrlInfo = {
  stream_type?: 'hls' | 'dash' | 'progressive'
  mpd_url?: string | null
  mpd_content?: string | null
  video_url?: string | null
  audio_url?: string | null
  default_quality_id?: string | null
  supports_manual_quality?: boolean
  qualities?: Array<{
    value: string
    label: string
    height?: number | null
    bandwidth?: number | null
    codec?: string
    id?: string | number | null
    index?: number
  }> | null
}

const toPlayerSourceType = (streamType?: VideoUrlInfo['stream_type']): MediaSource['type'] => {
  if (streamType === 'progressive') return 'native'
  return streamType || 'auto'
}

type DesktopWindow = Window & {
  desktopApp?: DesktopAppBridge
}

const isYouTubeUrl = (value: unknown) => {
  const url = String(value || '').trim().toLowerCase()
  if (!url) return false
  return url.includes('youtube.com/') || url.includes('youtu.be/')
}

const getDesktopBridge = () => {
  if (typeof window === 'undefined') return null
  const desktopWindow = window as DesktopWindow
  return desktopWindow.desktopApp || null
}

const resolveDesktopYouTubePlayback = async (
  videoUrl: string,
  options: VideoUrlOptions = {}
): Promise<VideoUrlInfo | null> => {
  const bridge = getDesktopBridge()
  if (bridge?.isDesktop !== true || typeof bridge.resolveYouTubePlayback !== 'function') {
    return null
  }

  return bridge.resolveYouTubePlayback(videoUrl, {
    forceRefresh: options.forceRefresh === true,
  })
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

  const getPlaybackSource = async (
    videoId: VideoId,
    options: VideoUrlOptions = {},
    playbackVideo: PlaybackVideoLike | null = null
  ): Promise<MediaSource> => {
    const { forceRefresh = false } = options
    if (!videoId) throw Object.assign(new Error('无效的视频ID'), { code: 'BAD_REQUEST' })

    try {
      let data: VideoUrlInfo | null | undefined
      let error: any = null
      const playbackUrl = String(playbackVideo?.url || '').trim()
      const isDesktopClient = isDesktopPlaybackClient()

      if (isDesktopClient && isYouTubeUrl(playbackUrl)) {
        Logger.debug('[getPlaybackSource] Resolving YouTube playback via desktop bridge', { videoId, forceRefresh })
        data = await resolveDesktopYouTubePlayback(playbackUrl, { forceRefresh })
      }

      if (!data) {
        // 统一通过后端获取播放链接（VideoUrlDto），后端会在 bilibili/YouTube 情况下返回 mpd_url 与可选清晰度
        Logger.debug('[getPlaybackSource] Fetching /api/video/url', { videoId, forceRefresh })
        const clientType = isDesktopClient ? 'desktop' : undefined
        const response = (await getVideoUrlInfo(videoId, { forceRefresh, clientType })) as ApiResult<VideoUrlInfo>
        data = response.data
        error = response.error
      }

      if (error) {
        const msg = error.data?.msg || error.message
        const errCode = extractErrorCode(msg) || error.data?.code || error.type || 'UNKNOWN'
        throw Object.assign(new Error(msg || '无法获取播放链接'), { code: errCode })
      }

      const mpdUrl = data?.mpd_url
      const mpdContent = data?.mpd_content
      const videoUrl = data?.video_url
      const audioUrl = data?.audio_url
      const streamType = data?.stream_type
      const qualities = (data?.qualities || []).map((item) => ({
        id: item.id ?? item.value,
        label: item.label,
        height: item.height ?? undefined,
        bitrate: item.bandwidth ?? undefined,
        codec: item.codec
      }))
      const shouldSynthesizeMpd = !data?.mpd_url && !!videoUrl && !!audioUrl && !isDesktopClient
      const synthesizedMpdUrl = shouldSynthesizeMpd
        ? `/api/video/mpd?video_id=${encodeURIComponent(String(videoId))}`
        : undefined

      const key = `${videoId}:${Date.now()}`
      const progressKey = String(videoId)
      const localMpdUrl = typeof mpdContent === 'string' && mpdContent.trim()
        ? URL.createObjectURL(new Blob([mpdContent], { type: 'application/dash+xml' }))
        : undefined
      const resolvedMpdUrl = localMpdUrl || mpdUrl || synthesizedMpdUrl
      const playbackEngine = localMpdUrl && isDesktopClient && isYouTubeUrl(playbackUrl)
        ? 'shaka'
        : undefined

      if (resolvedMpdUrl) return {
        src: resolvedMpdUrl,
        type: toPlayerSourceType(streamType),
        playbackEngine,
        key,
        progressKey,
        qualities
      }

      if (!videoUrl && !audioUrl) {
        throw Object.assign(new Error('无法获取播放链接'), { code: 'NO_STREAM_URL' })
      }

      return {
        src: videoUrl || audioUrl || '',
        type: toPlayerSourceType(streamType),
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
