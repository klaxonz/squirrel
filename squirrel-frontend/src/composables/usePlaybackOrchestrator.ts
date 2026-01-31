import { ref } from 'vue'
import useVideoDetail from './useVideoDetail'
import useRelatedVideos from './useRelatedVideos'
import useVideoOperations from './useVideoOperations'
import { Logger } from '@/utils/logger'

type VideoId = string | number

type VideoLike = {
  id: VideoId
  stream_video_url?: string
  mpd_url?: string
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
  const { video, startTime, fetchVideoDetails, maybeInjectSubtitles } = useVideoDetail(initialVideo)
  const { relatedVideos, loadingRelated, fetchRelatedVideos } = useRelatedVideos(video)
  const { playVideo } = useVideoOperations()
  const externalError = ref<ExternalErrorState | null>(null)

  const loadAndPlayById = async (
    videoId: VideoId,
    initialVideoData: VideoLike | null = null,
    options: PlayOptions = {}
  ) => {
    if (!videoId) return
    Logger.debug('[usePlaybackOrchestrator] loadAndPlayById start', videoId)

    if (initialVideoData && initialVideoData.id === videoId) {
      video.value = initialVideoData as any
    }

    const hasInitialData = !!video.value && (video.value as any).id === videoId

    if (!hasInitialData) {
      await fetchVideoDetails(videoId as any)
    } else {
      fetchVideoDetails(videoId as any).catch((e) => Logger.error('[usePlaybackOrchestrator] fetchVideoDetails error', e))
    }

    Logger.debug('[usePlaybackOrchestrator] after fetchVideoDetails', {
      hasStreamUrl: !!(video.value as any)?.stream_video_url,
      hasMpdUrl: !!(video.value as any)?.mpd_url,
    })

    try {
      await maybeInjectSubtitles(videoId as any)
    } catch (_) {}

    await fetchRelatedVideos()

    externalError.value = null

    Logger.debug('[usePlaybackOrchestrator] calling playVideo (non-blocking)')
    ;(async () => {
      try {
        await playVideo(video.value as any, options)
      } catch (err) {
        const e = toRecord(err)
        const code = String(e.code || 'FAILED')
        const message = String(e.message || '播放链接获取失败')
        externalError.value = {
          code,
          title: '播放失败',
          message,
          canRetry: true,
        }
      }
    })()

    Logger.debug('[usePlaybackOrchestrator] playVideo invoked', {
      hasStreamUrl: !!(video.value as any)?.stream_video_url,
      hasMpdUrl: !!(video.value as any)?.mpd_url,
    })
  }

  return {
    // state
    video,
    startTime,
    relatedVideos,
    loadingRelated,
    externalError,

    // actions
    loadAndPlayById,
  }
}


