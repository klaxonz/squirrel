import { Logger } from '@/shared/lib/logger'
import { getDesktopBridge } from '@/shared/composables/useDesktopBridge'
import type {
  MediaSource,
  SabrPlaybackSession,
} from '@/features/playback/components/video-player/core'

type VideoId = string | number

type VideoUrlOptions = {
  forceRefresh?: boolean
}

type PlaybackVideoLike = {
  url?: string | null
  title?: string | null
}

export type VideoUrlInfo = {
  stream_type?: 'hls' | 'dash' | 'progressive' | 'sabr'
  mpd_url?: string | null
  mpd_content?: string | null
  fallback_mpd_content?: string | null
  sabr?: {
    server_abr_url: string
    ustreamer_config: string
    formats: SabrPlaybackSession['formats']
    client_info: SabrPlaybackSession['clientInfo']
    po_token: string
  } | null
  video_url?: string | null
  audio_url?: string | null
  title?: string | null
  thumbnail?: string | null
  uploader_name?: string | null
  uploader_url?: string | null
  uploader_avatar?: string | null
  default_quality_id?: string | null
  supports_manual_quality?: boolean
  metadata?: Record<string, unknown>
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
  if (streamType === 'sabr') return 'dash'
  return streamType || 'auto'
}

const toDashDataUrl = (manifest: string) =>
  `data:application/dash+xml;charset=UTF-8,${encodeURIComponent(manifest)}`

const normalizeSabrSession = (value: VideoUrlInfo['sabr']): SabrPlaybackSession | null => {
  if (
    !value
    || !value.server_abr_url
    || !value.ustreamer_config
    || !value.po_token
    || !Number.isFinite(value.client_info?.clientName)
    || !Array.isArray(value.formats)
    || value.formats.length === 0
  ) {
    return null
  }

  return {
    serverAbrUrl: value.server_abr_url,
    ustreamerConfig: value.ustreamer_config,
    formats: value.formats,
    clientInfo: value.client_info,
    poToken: value.po_token,
  }
}

export const DESKTOP_PLAYBACK_TIMEOUT_MS = 120000

export type DesktopResolverKey =
  | 'resolveYouTubePlayback'
  | 'resolveBilibiliPlayback'

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

  if (getDesktopBridge()?.isDesktop === true) return true
  if (typeof navigator === 'undefined') return false

  const userAgent = String(navigator.userAgent || '')
  return /electron|tauri/i.test(userAgent)
}

/**
 * Best-effort warm of the desktop provider cache while the user is still on a
 * list/history card. Resolve is identity-scoped and short-lived; a hit removes
 * the full youtubei + PO-token round trip from first paint.
 */
export const prefetchDesktopPlaybackSource = (
  playbackVideo: PlaybackVideoLike & { id?: VideoId | null } | null | undefined,
): void => {
  if (!isDesktopPlaybackClient()) return

  const videoUrl = String(playbackVideo?.url || '').trim()
  if (!videoUrl) return

  const provider = findDesktopPlaybackProvider(videoUrl)
  if (!provider) return

  void resolveDesktopPlayback(provider, videoUrl, {}, playbackVideo).catch((error) => {
    Logger.debug('[prefetchDesktopPlaybackSource] skipped', {
      url: videoUrl,
      error: error instanceof Error ? error.message : String(error || 'unknown'),
    })
  })
}

export default function useVideoOperations() {
  const getPlaybackSource = async (
    videoId: VideoId,
    options: VideoUrlOptions = {},
    playbackVideo: PlaybackVideoLike | null = null
  ): Promise<MediaSource> => {
    const { forceRefresh = false } = options
    if (!videoId) throw Object.assign(new Error('无效的视频编号'), { code: 'BAD_REQUEST' })

    const playbackUrl = String(playbackVideo?.url || '').trim()
    const isDesktopClient = isDesktopPlaybackClient()
    const matchedDesktopProvider = findDesktopPlaybackProvider(playbackUrl)

    if (!isDesktopClient) {
      throw Object.assign(new Error('当前环境不支持播放'), { code: 'PLAYBACK_DESKTOP_REQUIRED' })
    }

    if (!matchedDesktopProvider) {
      throw Object.assign(new Error('当前站点不支持桌面端播放'), { code: 'UNSUPPORTED_PLAYBACK_SITE' })
    }

    Logger.debug(`[getPlaybackSource] Resolving ${matchedDesktopProvider.debugLabel} playback via desktop bridge`, { videoId, forceRefresh })
    const data = await resolveDesktopPlayback(matchedDesktopProvider, playbackUrl, { forceRefresh }, playbackVideo)
    if (!data) {
        throw Object.assign(new Error('桌面端播放解析不可用'), { code: 'DESKTOP_PLAYBACK_UNAVAILABLE' })
      }

      const mpdUrl = data?.mpd_url
      const mpdContent = data?.mpd_content
      const fallbackMpdContent = data?.fallback_mpd_content
      const videoUrl = data?.video_url
      const audioUrl = data?.audio_url
      const streamType = data?.stream_type
      const qualities = (data?.qualities || []).map((item, index) => {
        const id = item.id ?? item.value ?? index
        const height = item.height ?? undefined
        const label = String(
          item.label
          || (typeof height === 'number' && height > 0 ? `${height}p` : '')
          || id
        ).trim()
        return {
          id,
          label,
          height,
          bitrate: item.bandwidth ?? undefined,
          codec: item.codec,
          src: item.src ?? undefined,
        }
      }).filter((item) => item.id !== undefined && item.id !== null && item.label)
      const key = `${videoId}:${Date.now()}`
      const progressKey = String(videoId)
      // Keep YouTube manifests inline so the MPD never needs another fetch.
      // SABR uses the same DASH XML container with custom sabr: BaseURLs.
      const trimmedMpd = typeof mpdContent === 'string' ? mpdContent.trim() : ''
      const trimmedFallbackMpd = typeof fallbackMpdContent === 'string'
        ? fallbackMpdContent.trim()
        : ''
      const sabrSession = streamType === 'sabr' ? normalizeSabrSession(data.sabr) : null
      const isYouTubeSabr =
        matchedDesktopProvider.site === 'youtube'
        && streamType === 'sabr'
        && Boolean(trimmedMpd)
        && Boolean(sabrSession)
      const isYouTubeOfficialDash = matchedDesktopProvider.site === 'youtube'
        && (streamType === 'dash' || streamType === 'sabr')
      // If an older/malformed bridge response advertises SABR without its
      // session payload, start directly on the bundled regular DASH fallback.
      const playbackMpd = streamType === 'sabr' && !isYouTubeSabr
        ? trimmedFallbackMpd
        : trimmedMpd
      const localMpdUrl = playbackMpd
        ? (isYouTubeOfficialDash
          ? toDashDataUrl(playbackMpd)
          : URL.createObjectURL(new Blob([playbackMpd], { type: 'application/dash+xml' })))
        : undefined
      const resolvedMpdUrl = localMpdUrl || mpdUrl

      const resolvedMetadata = { ...(data?.metadata || {}) } as Record<string, unknown>
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
        // Both YouTube SABR and its DASH fallback require Shaka. dash.js has no
        // UMP/SABR transport and lacks the legacy POST/alr rewrite path.
        ...(isYouTubeOfficialDash ? { playbackEngine: 'shaka' as const } : {}),
        ...(isYouTubeSabr && sabrSession ? {
          sabr: {
            ...sabrSession,
            fallbackSrc: trimmedFallbackMpd ? toDashDataUrl(trimmedFallbackMpd) : undefined,
            refresh: async () => {
              const refreshed = await resolveDesktopPlayback(
                matchedDesktopProvider,
                playbackUrl,
                { forceRefresh: true },
                playbackVideo,
              )
              return normalizeSabrSession(refreshed?.sabr)
            },
          },
        } : {}),
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
  }

  return {
    getPlaybackSource,
  }
}
