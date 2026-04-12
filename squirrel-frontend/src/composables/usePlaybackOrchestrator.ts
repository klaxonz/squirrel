import { ref, watch } from 'vue'
import useVideoDetail from './useVideoDetail'
import useRelatedVideos from './useRelatedVideos'
import useVideoOperations from './useVideoOperations'
import { Logger } from '@/utils/logger'
import type { MediaSource } from '@/components/video-player/core'
import type { SubtitleTrack } from '@/components/video-player/plugins/subtitles'

type VideoId = string | number

type VideoLike = {
  id: VideoId
  [key: string]: unknown
}

type ExternalErrorState = {
  code: string
  title: string
  message: string
  canRetry: boolean
}

type PlayOptions = Record<string, unknown>

const toRecord = (value: unknown): Record<string, any> => {
  if (value && typeof value === 'object') return value as Record<string, any>
  return {}
}

export default function usePlaybackOrchestrator(initialVideo: VideoLike | null = null) {
  const { video, startTime, fetchVideoDetails, maybeInjectSubtitles, setVideoSnapshot } = useVideoDetail(initialVideo)
  const { relatedVideos, loadingRelated, fetchRelatedVideos, setRelatedVideosSnapshot } = useRelatedVideos(video)
  const { getPlaybackSource } = useVideoOperations()
  const playbackSource = ref<MediaSource | null>(null)
  const subtitleTracks = ref<SubtitleTrack[]>([])
  const externalError = ref<ExternalErrorState | null>(null)
  const isResolvingPlayback = ref(false)
  const requestSeq = ref(0)

  const loadAndPlayById = async (
    videoId: VideoId,
    initialVideoData: VideoLike | null = null,
    options: PlayOptions = {}
  ) => {
    if (!videoId) return

    requestSeq.value += 1
    const seq = requestSeq.value

    Logger.debug('[usePlaybackOrchestrator] loadAndPlayById start', { videoId, seq })

    externalError.value = null
    isResolvingPlayback.value = true
    playbackSource.value = null
    subtitleTracks.value = []

    const currentVideoId = video.value && (video.value as any).id != null ? String((video.value as any).id) : ''
    const targetVideoId = String(videoId)

    if (initialVideoData && initialVideoData.id === videoId) {
      setVideoSnapshot(initialVideoData as any)
    }
    if (!initialVideoData && currentVideoId && currentVideoId !== targetVideoId) {
      setVideoSnapshot(null)
    }

    const hasInitialData = !!video.value && (video.value as any).id === videoId
    const playbackPromise = getPlaybackSource(videoId, options)
    const detailPromise = !hasInitialData
      ? fetchVideoDetails(videoId as any).catch((e) => {
          Logger.error('[usePlaybackOrchestrator] fetchVideoDetails error', e)
          return null
        })
      : fetchVideoDetails(videoId as any).catch((e) => {
          Logger.error('[usePlaybackOrchestrator] fetchVideoDetails error', e)
          return null
        })

    Promise.resolve(detailPromise).then(() => {
      Logger.debug('[usePlaybackOrchestrator] after fetchVideoDetails', {
        hasVideo: !!video.value,
      })
      if (seq !== requestSeq.value) return

      maybeInjectSubtitles(videoId as any).catch((e) =>
        Logger.error('[usePlaybackOrchestrator] maybeInjectSubtitles error', e)
      )
      fetchRelatedVideos(videoId as any).catch((e) =>
        Logger.error('[usePlaybackOrchestrator] fetchRelatedVideos error', e)
      )
    })

    try {
      const source = await playbackPromise
      if (seq !== requestSeq.value) return

      const v: any = video.value || initialVideoData || {}
      playbackSource.value = {
        ...source,
        poster: source.poster || v.thumbnail,
        title: source.title || v.title,
      }

      Logger.debug('[usePlaybackOrchestrator] playbackSource ready', {
        videoId,
        src: playbackSource.value?.src,
      })
    } catch (err) {
      if (seq !== requestSeq.value) return

      const e = toRecord(err)
      const code = String(e.code || 'FAILED')
      const message = String(e.message || '播放链接获取失败')
      externalError.value = {
        code,
        title: '播放失败',
        message,
        canRetry: true,
      }
    } finally {
      if (seq === requestSeq.value) {
        isResolvingPlayback.value = false
      }
    }
  }

  const toSubtitleTracks = (subtitles: unknown): SubtitleTrack[] => {
    if (!Array.isArray(subtitles)) return []

    return subtitles.map((item, i) => {
      const s = toRecord(item)
      const id = String(s.id || `sub-${i}`)
      const language = String(s.language || s.lang || 'unknown')
      const label = String(s.label || s.name || language || `Subtitle ${i + 1}`)
      const url = typeof s.url === 'string'
        ? s.url
        : (typeof s.src === 'string' ? s.src : undefined)
      const content = typeof s.content === 'string' ? s.content : undefined
      const isDefault = s.default === true

      return {
        id,
        label,
        language,
        url,
        content,
        default: isDefault || (!subtitles.some((x: any) => toRecord(x).default === true) && i === 0),
      }
    })
  }

  const hydratePlaybackState = ({
    videoSnapshot = null,
    nextPlaybackSource = null,
    nextSubtitleTracks = [],
    nextExternalError = null,
    nextIsResolvingPlayback = false,
    nextRelatedVideos = [],
    nextLoadingRelated = false,
  }: {
    videoSnapshot?: VideoLike | null
    nextPlaybackSource?: MediaSource | null
    nextSubtitleTracks?: SubtitleTrack[]
    nextExternalError?: ExternalErrorState | null
    nextIsResolvingPlayback?: boolean
    nextRelatedVideos?: VideoLike[]
    nextLoadingRelated?: boolean
  } = {}) => {
    requestSeq.value += 1
    setVideoSnapshot(videoSnapshot)
    playbackSource.value = nextPlaybackSource
    subtitleTracks.value = Array.isArray(nextSubtitleTracks) ? [...nextSubtitleTracks] : []
    externalError.value = nextExternalError
    isResolvingPlayback.value = !!nextIsResolvingPlayback
    setRelatedVideosSnapshot(nextRelatedVideos as any[], nextLoadingRelated)
  }

  watch(
    () => toRecord(video.value as any)?.subtitles,
    (subtitles) => {
      subtitleTracks.value = toSubtitleTracks(subtitles)
    },
    { immediate: true, deep: true }
  )

  return {
    // state
    video,
    startTime,
    relatedVideos,
    loadingRelated,
    playbackSource,
    subtitleTracks,
    externalError,
    isResolvingPlayback,
    hydratePlaybackState,

    // actions
    loadAndPlayById,
  }
}

