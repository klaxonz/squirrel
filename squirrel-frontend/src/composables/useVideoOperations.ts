import { getVideoUrlInfo } from '@/api'
import { Logger } from '@/utils/logger'
import type { MediaSource } from '@/components/video-player/core'

type VideoId = string | number

type VideoUrlOptions = {
  forceRefresh?: boolean
}

type PlaybackVideoLike = {
  url?: string | null
  title?: string | null
}

type ApiResult<T> = { data?: T | null; error?: any }

export type VideoUrlInfo = {
  stream_type?: 'hls' | 'dash' | 'progressive'
  mpd_url?: string | null
  mpd_content?: string | null
  video_url?: string | null
  audio_url?: string | null
  title?: string | null
  thumbnail?: string | null
  uploader_name?: string | null
  uploader_url?: string | null
  uploader_avatar?: string | null
  default_quality_id?: string | null
  supports_manual_quality?: boolean
  metadata?: Record<string, any>
  qualities?: Array<{
    value: string
    label: string
    height?: number | null
    bandwidth?: number | null
    codec?: string
    src?: string | null
    id?: string | number | null
    index?: number
  }> | null
}

export const toPlayerSourceType = (streamType?: VideoUrlInfo['stream_type']): MediaSource['type'] => {
  if (streamType === 'progressive') return 'native'
  return streamType || 'auto'
}

type DesktopWindow = Window & {
  desktopApp?: DesktopAppBridge
}

const getDesktopBridge = () => {
  if (typeof window === 'undefined') return null
  const desktopWindow = window as DesktopWindow
  return desktopWindow.desktopApp || null
}

export const DESKTOP_PLAYBACK_TIMEOUT_MS = 120000

export type DesktopResolverKey =
  | 'resolveYouTubePlayback'
  | 'resolveBilibiliPlayback'
  | 'resolveJavdbPlayback'
  | 'resolvePornhubPlayback'
  | 'resolveYouPornPlayback'

export type DesktopPlaybackProvider = {
  site: string
  key: DesktopResolverKey
  matches: (url: string) => boolean
  debugLabel: string
}

const includesAny = (value: string, needles: string[]) => needles.some((needle) => value.includes(needle))

export const DESKTOP_PLAYBACK_PROVIDERS: DesktopPlaybackProvider[] = [
  {
    site: 'youtube',
    key: 'resolveYouTubePlayback',
    debugLabel: 'YouTube',
    matches: (url) => includesAny(url, ['youtube.com/', 'youtu.be/']),
  },
  {
    site: 'bilibili',
    key: 'resolveBilibiliPlayback',
    debugLabel: 'Bilibili',
    matches: (url) => includesAny(url, ['bilibili.com/video/', 'b23.tv/']),
  },
  {
    site: 'javdb',
    key: 'resolveJavdbPlayback',
    debugLabel: 'JavDB',
    matches: (url) => includesAny(url, ['javdb.com/v/', 'javdb.com/video/']),
  },
  {
    site: 'pornhub',
    key: 'resolvePornhubPlayback',
    debugLabel: 'Pornhub',
    matches: (url) => includesAny(url, ['pornhub.com/view_video.php', 'pornhub.com/video/', 'pornhub.com/embed/']),
  },
  {
    site: 'youporn',
    key: 'resolveYouPornPlayback',
    debugLabel: 'YouPorn',
    matches: (url) => includesAny(url, ['youporn.com/watch/', 'you-porn.com/watch/']),
  },
]

export const findDesktopPlaybackProvider = (url: string) => {
  const value = String(url || '').trim()
  if (!value) return null
  return DESKTOP_PLAYBACK_PROVIDERS.find((provider) => provider.matches(value)) || null
}

export const resolveDesktopPlayback = async (
  provider: DesktopPlaybackProvider,
  videoUrl: string,
  options: VideoUrlOptions = {},
  playbackVideo: PlaybackVideoLike | null = null,
): Promise<VideoUrlInfo | null> => {
  const bridge = getDesktopBridge()
  const resolver = bridge?.[provider.key]
  if (bridge?.isDesktop !== true || typeof resolver !== 'function') {
    return null
  }

  let timer: ReturnType<typeof setTimeout> | undefined
  try {
    return await Promise.race([
      resolver(videoUrl, {
        forceRefresh: options.forceRefresh === true,
        title: playbackVideo?.title || undefined,
      }),
      new Promise<never>((_, reject) => {
        timer = setTimeout(() => reject(new Error(`${provider.debugLabel} desktop playback timed out`)), DESKTOP_PLAYBACK_TIMEOUT_MS)
      }),
    ])
  } finally {
    if (timer) clearTimeout(timer)
  }
}

export const isDesktopPlaybackClient = () => {
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
    if (!videoId) throw Object.assign(new Error('无效的视频编号'), { code: 'BAD_REQUEST' })

    try {
      let data: VideoUrlInfo | null | undefined
      let error: any = null
      const playbackUrl = String(playbackVideo?.url || '').trim()
      const isDesktopClient = isDesktopPlaybackClient()
      const matchedDesktopProvider = findDesktopPlaybackProvider(playbackUrl)

      if (isDesktopClient && matchedDesktopProvider) {
        Logger.debug(`[getPlaybackSource] Resolving ${matchedDesktopProvider.debugLabel} playback via desktop bridge`, { videoId, forceRefresh })
        data = await resolveDesktopPlayback(matchedDesktopProvider, playbackUrl, { forceRefresh }, playbackVideo)
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
        codec: item.codec,
        src: item.src ?? undefined
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

      const resolvedMetadata = { ...(data?.metadata || {}) } as Record<string, any>
      const uploaderName = String(data?.uploader_name || '').trim()
      const uploaderUrl = String(data?.uploader_url || '').trim()
      const uploaderAvatar = String(data?.uploader_avatar || '').trim()
      if (data?.title || data?.thumbnail || uploaderName) {
        const metadataVideo = (resolvedMetadata.video && typeof resolvedMetadata.video === 'object')
          ? resolvedMetadata.video
          : {}
        resolvedMetadata.video = {
          ...metadataVideo,
          title: data?.title || undefined,
          thumbnail: data?.thumbnail || undefined,
          subscriptions: uploaderName ? [{
            name: uploaderName,
            url: uploaderUrl,
            avatar: uploaderAvatar,
          }] : undefined,
        }
      }

      if (resolvedMpdUrl) return {
        src: resolvedMpdUrl,
        type: toPlayerSourceType(streamType),
        key,
        progressKey,
        qualities,
        metadata: resolvedMetadata,
      }

      if (!videoUrl && !audioUrl) {
        throw Object.assign(new Error('无法获取播放链接'), { code: 'NO_STREAM_URL' })
      }

      return {
        src: videoUrl || audioUrl || '',
        type: toPlayerSourceType(streamType),
        key,
        progressKey,
        qualities,
        metadata: resolvedMetadata,
      }
    } catch (err) {
      throw err
    }
  }

  return {
    getPlaybackSource,
  }
}
