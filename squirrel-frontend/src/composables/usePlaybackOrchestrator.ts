import { ref } from 'vue'
import useVideoDetail from './useVideoDetail'
import useRelatedVideos from './useRelatedVideos'
import useVideoOperations from './useVideoOperations'
import { Logger } from '@/utils/logger'
import type { MediaSource } from '@/components/video-player/core'

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
  const { video, startTime, fetchVideoDetails, maybeInjectSubtitles } = useVideoDetail(initialVideo)
  const { relatedVideos, loadingRelated, fetchRelatedVideos } = useRelatedVideos(video)
  const { getPlaybackSource } = useVideoOperations()
  const playbackSource = ref<MediaSource | null>(null)
  const externalError = ref<ExternalErrorState | null>(null)
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
    playbackSource.value = null

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
      hasVideo: !!video.value,
    })

    try {
      await maybeInjectSubtitles(videoId as any)
    } catch (_) {}

    await fetchRelatedVideos()

    if (seq !== requestSeq.value) return

    try {
      const source = await getPlaybackSource(videoId, options)
      if (seq !== requestSeq.value) return

      const v: any = video.value || {}
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
    }
  }

  return {
    // state
    video,
    startTime,
    relatedVideos,
    loadingRelated,
    playbackSource,
    externalError,

    // actions
    loadAndPlayById,
  }
}


