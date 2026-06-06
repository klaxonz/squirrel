import { ref, watch } from 'vue'
import useVideoDetail from './useVideoDetail'
import useRelatedVideos from './useRelatedVideos'
import useVideoOperations from './useVideoOperations'
import { Logger } from '@/utils/logger'
import type { MediaSource } from '@/components/video-player/core'
import type { SubtitleTrack } from '@/components/video-player/plugins/subtitles'
import type { VideoId, VideoPageVideo, VideoProfile } from '@/types/videoPlayback'

export type ExternalErrorState = {
  code: string
  title: string
  message: string
  canRetry: boolean
}

type PlayOptions = Record<string, unknown>

const toRecord = (value: unknown): Record<string, unknown> => {
  if (value && typeof value === 'object') return value as Record<string, unknown>
  return {}
}

const actorKey = (actor: VideoProfile) => {
  const url = String(actor.url || '').trim().toLowerCase()
  if (url) return `url:${url}`
  const id = String(actor.id || '').trim()
  if (id) return `id:${id}`
  const name = String(actor.name || '').trim().toLowerCase()
  return name ? `name:${name}` : ''
}

const mergeActor = (currentActor: VideoProfile, nextActor: VideoProfile) => {
  const merged: Record<string, unknown> = { ...currentActor }
  for (const [key, value] of Object.entries(nextActor)) {
    if (value != null && value !== '' && (merged[key] == null || merged[key] === '')) {
      merged[key] = value
    }
  }
  return merged as VideoProfile
}

const mergeActors = (currentActors: unknown, nextActors: VideoProfile[]) => {
  const mergedActors = Array.isArray(currentActors)
    ? currentActors.map((actor) => ({ ...toRecord(actor) } as VideoProfile))
    : []
  const indexByKey = new Map<string, number>()

  mergedActors.forEach((actor, index) => {
    const key = actorKey(actor)
    if (key) indexByKey.set(key, index)
  })

  for (const actor of nextActors) {
    const key = actorKey(actor)
    const existingIndex = key ? indexByKey.get(key) : undefined
    if (existingIndex != null) {
      mergedActors[existingIndex] = mergeActor(mergedActors[existingIndex], actor)
      continue
    }
    mergedActors.push(actor)
    if (key) indexByKey.set(key, mergedActors.length - 1)
  }

  return mergedActors
}

export const mergeVideoMetadata = (currentVideo: VideoPageVideo | null, videoMetadata: Record<string, unknown>, sourceUrl = '') => {
  if (!currentVideo || !videoMetadata || Object.keys(videoMetadata).length === 0) return currentVideo

  const currentUrl = String(currentVideo.url || '')
  if (sourceUrl && currentUrl && sourceUrl !== currentUrl) return currentVideo

  const nextVideo: VideoPageVideo = { ...currentVideo }
  if (typeof videoMetadata.title === 'string' && videoMetadata.title) {
    nextVideo.title = videoMetadata.title
  }
  if (typeof videoMetadata.thumbnail === 'string' && videoMetadata.thumbnail) {
    nextVideo.thumbnail = videoMetadata.thumbnail
  }
  if (typeof videoMetadata.publish_date === 'string' && videoMetadata.publish_date) {
    nextVideo.publish_date = videoMetadata.publish_date
  }
  if (typeof videoMetadata.duration === 'number') {
    nextVideo.duration = videoMetadata.duration
  }

  if (Array.isArray(videoMetadata.actors) && videoMetadata.actors.length > 0) {
    nextVideo.actors = mergeActors(nextVideo.actors, videoMetadata.actors.map((actor) => toRecord(actor) as VideoProfile))
  }

  if (Array.isArray(videoMetadata.subscriptions) && videoMetadata.subscriptions.length > 0) {
    nextVideo.subscriptions = mergeActors(nextVideo.subscriptions, videoMetadata.subscriptions.map((subscription) => toRecord(subscription) as VideoProfile))
  }

  return nextVideo
}

const mergePlaybackMetadata = (currentVideo: VideoPageVideo | null, playbackMetadata: Record<string, unknown>) => {
  return mergeVideoMetadata(currentVideo, toRecord(playbackMetadata.video), String(playbackMetadata.source_url || ''))
}

type DesktopWindow = Window & {
  desktopApp?: { isDesktop?: boolean }
}

const isDesktopPlaybackClient = () => {
  if (typeof window === 'undefined') return false
  const desktopWindow = window as DesktopWindow
  if (desktopWindow.desktopApp?.isDesktop === true) return true
  if (typeof navigator === 'undefined') return false
  return /electron|tauri/i.test(String(navigator.userAgent || ''))
}

export default function usePlaybackOrchestrator(initialVideo: VideoPageVideo | null = null) {
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
    initialVideoData: VideoPageVideo | null = null,
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

    const currentVideoId = video.value?.id != null ? String(video.value.id) : ''
    const targetVideoId = String(videoId)

    if (initialVideoData && initialVideoData.id === videoId) {
      setVideoSnapshot(initialVideoData)
    }
    if (!initialVideoData && currentVideoId && currentVideoId !== targetVideoId) {
      setVideoSnapshot(null)
    }

    const hasInitialData = !!video.value && video.value.id === videoId
    const detailPromise = !hasInitialData
      ? fetchVideoDetails(videoId).catch((e) => {
          Logger.error('[usePlaybackOrchestrator] fetchVideoDetails error', e)
          return null
        })
      : fetchVideoDetails(videoId).catch((e) => {
          Logger.error('[usePlaybackOrchestrator] fetchVideoDetails error', e)
          return null
        })
    const playbackPromise = (async () => {
      const initialPlaybackVideo = (() => {
        if (initialVideoData && typeof initialVideoData.url === 'string') {
          return initialVideoData
        }
        if (hasInitialData && typeof video.value?.url === 'string') {
          return video.value
        }
        return null
      })()

      if (initialPlaybackVideo) {
        return getPlaybackSource(videoId, options, initialPlaybackVideo)
      }

      if (isDesktopPlaybackClient()) {
        const detailedVideo = await detailPromise
        if (detailedVideo && typeof detailedVideo.url === 'string') {
          return getPlaybackSource(videoId, options, detailedVideo)
        }
      }

      return getPlaybackSource(videoId, options, null)
    })()

    Promise.resolve(detailPromise).then(() => {
      Logger.debug('[usePlaybackOrchestrator] after fetchVideoDetails', {
        hasVideo: !!video.value,
      })
      if (seq !== requestSeq.value) return

      maybeInjectSubtitles(videoId).catch((e) =>
        Logger.error('[usePlaybackOrchestrator] maybeInjectSubtitles error', e)
      )
      fetchRelatedVideos(videoId).catch((e) =>
        Logger.error('[usePlaybackOrchestrator] fetchRelatedVideos error', e)
      )
    })

    try {
      const source = await playbackPromise
      await detailPromise
      if (seq !== requestSeq.value) return

      const v = video.value || initialVideoData || null
      const sourceMetadata = 'metadata' in source ? source.metadata : undefined
      const mergedVideo = mergePlaybackMetadata(v, toRecord(sourceMetadata))
      if (mergedVideo && mergedVideo !== video.value) {
        setVideoSnapshot(mergedVideo)
      }
      playbackSource.value = {
        ...source,
        title: source.title || mergedVideo?.title || v?.title || '',
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
        default: isDefault || (!subtitles.some((x) => toRecord(x).default === true) && i === 0),
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
    videoSnapshot?: VideoPageVideo | null
    nextPlaybackSource?: MediaSource | null
    nextSubtitleTracks?: SubtitleTrack[]
    nextExternalError?: ExternalErrorState | null
    nextIsResolvingPlayback?: boolean
    nextRelatedVideos?: VideoPageVideo[]
    nextLoadingRelated?: boolean
  } = {}) => {
    requestSeq.value += 1
    setVideoSnapshot(videoSnapshot)
    playbackSource.value = nextPlaybackSource
    subtitleTracks.value = Array.isArray(nextSubtitleTracks) ? [...nextSubtitleTracks] : []
    externalError.value = nextExternalError
    isResolvingPlayback.value = !!nextIsResolvingPlayback
    setRelatedVideosSnapshot(nextRelatedVideos, nextLoadingRelated)
  }

  watch(
    () => video.value?.subtitles,
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
