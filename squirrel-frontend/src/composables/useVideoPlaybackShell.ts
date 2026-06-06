import { onMounted, onUnmounted, ref, watch } from 'vue'
import type { Ref } from 'vue'

import { Logger } from '@/utils/logger'
import type { ClipMarker, VideoId, VideoPageVideo, VideoProfile } from '@/types/videoPlayback'
import type { MediaSource } from '@/components/video-player/core'
import type { SubtitleTrack } from '@/components/video-player/plugins/subtitles'
import type { ExternalErrorState } from './usePlaybackOrchestrator'

type PlaybackSourceLike = MediaSource | null
type VideoSeedGetter = (videoId: unknown) => VideoPageVideo | null

type RouteLike = {
  params: Record<string, unknown>
}

type GlobalPlaybackSessionLike = {
  currentVideoId?: string | number | null
  source?: PlaybackSourceLike
  uploader?: string
  externalError?: ExternalErrorState | null
  externalLoading?: boolean
  videoSnapshot?: VideoPageVideo | null
  subtitles?: SubtitleTrack[]
  relatedVideos?: VideoPageVideo[]
  loadingRelated?: boolean
  pictureInPicture?: boolean
}

type ActivateSessionPayload = {
  target: HTMLElement | null
  source: PlaybackSourceLike
  subtitles: SubtitleTrack[]
  clipMarkers: ClipMarker[]
  title: string
  uploader: string
  initialTime: number | null | undefined
  hasPrev: boolean
  hasNext: boolean
  externalError: ExternalErrorState | null
  widescreen: boolean
  externalLoading: boolean
  adapter: unknown
  theme: unknown
  currentVideoId: string
  videoSnapshot: VideoPageVideo | null
  relatedVideos: VideoPageVideo[]
  loadingRelated: boolean
  handlers: {
    onPlay: (() => void) | null
    onPause: (() => void) | null
    onEnded: ((event?: { autoplay?: boolean; autoplayNext?: boolean; loop?: boolean }) => void | Promise<void>) | null
    onTimeUpdate: ((currentTime: number) => void) | null
    onPrev: (() => void | Promise<void>) | null
    onNext: (() => void | Promise<void>) | null
    onRetry: (() => void | Promise<void>) | null
    onWidescreenChange: ((enabled: boolean) => void) | null
    onClipMarkerSelect: ((time: number) => void | Promise<void>) | null
    onClipMarkersUpdated: ((markers: ClipMarker[]) => void) | null
  }
}

import { useUIStore } from '@/stores/ui'

export default function useVideoPlaybackShell({
  route,
  playerAdapter,
  video,
  playbackSource,
  subtitleTracks,
  resolvedInitialTime,
  clipMarkers,
  hasPrevVideo,
  hasNextVideo,
  externalError,
  isResolvingPlayback,
  effectiveTheme,
  relatedVideos,
  loadingRelated,
  hasPrev,
  hasNext,
  globalVideoPlayerSession,
  activateGlobalVideoPlayerSession,
  clearGlobalVideoPlayerSession,
  registerGlobalVideoPlayerTarget,
  unregisterGlobalVideoPlayerTarget,
  focusGlobalVideoPlayer,
  hydratePlaybackState,
  loadAndPlayById,
  consumePlaybackSeed,
  onVideoPlay,
  onVideoPause,
  handleAutoplayNext,
  handlePlaybackTimeUpdate,
  handlePrevVideoFromPlaylist,
  handleNextVideoFromPlaylist,
  handlePlayerRetry,
  handleClipMarkerSeek,
  handleClipMarkersUpdated,
  flushPendingReport,
}: {
  route: RouteLike
  playerAdapter: unknown
  video: Ref<VideoPageVideo | null>
  playbackSource: Ref<PlaybackSourceLike>
  subtitleTracks: Ref<SubtitleTrack[]>
  resolvedInitialTime: Ref<number | null | undefined>
  clipMarkers: Ref<ClipMarker[]>
  hasPrevVideo: Ref<boolean>
  hasNextVideo: Ref<boolean>
  externalError: Ref<ExternalErrorState | null>
  isResolvingPlayback: Ref<boolean>
  effectiveTheme: Ref<unknown>
  relatedVideos: Ref<VideoPageVideo[]>
  loadingRelated: Ref<boolean>
  hasPrev: Ref<boolean>
  hasNext: Ref<boolean>
  globalVideoPlayerSession: GlobalPlaybackSessionLike
  activateGlobalVideoPlayerSession: (payload: ActivateSessionPayload) => void
  clearGlobalVideoPlayerSession: () => void
  registerGlobalVideoPlayerTarget: (target: HTMLElement) => void
  unregisterGlobalVideoPlayerTarget: () => void
  focusGlobalVideoPlayer: () => Promise<void>
  hydratePlaybackState: (payload: {
    videoSnapshot: VideoPageVideo | null
    nextPlaybackSource: PlaybackSourceLike
    nextSubtitleTracks: SubtitleTrack[]
    nextExternalError: ExternalErrorState | null
    nextIsResolvingPlayback: boolean | undefined
    nextRelatedVideos: VideoPageVideo[]
    nextLoadingRelated: boolean | undefined
  }) => void
  loadAndPlayById: (videoId: VideoId, initialVideoData?: VideoPageVideo | null, options?: Record<string, unknown>) => Promise<void>
  consumePlaybackSeed: VideoSeedGetter
  onVideoPlay: () => void
  onVideoPause: () => void
  handleAutoplayNext: (event?: { autoplay?: boolean; autoplayNext?: boolean; loop?: boolean }) => void | Promise<void>
  handlePlaybackTimeUpdate: (currentTime: number) => void
  handlePrevVideoFromPlaylist: () => void | Promise<void>
  handleNextVideoFromPlaylist: () => void | Promise<void>
  handlePlayerRetry: () => void | Promise<void>
  handleClipMarkerSeek: (time: number) => void | Promise<void>
  handleClipMarkersUpdated: (markers: ClipMarker[]) => void
  flushPendingReport: () => Promise<void>
}) {
  const uiStore = useUIStore()
  const videoPlayerHostRef = ref<HTMLElement | null>(null)
  const videoPageRef = ref<HTMLElement | null>(null)
  const videoSectionRef = ref<HTMLElement | null>(null)
  const videoMetaRef = ref<HTMLElement | null>(null)
  const isWidescreen = ref(false)

  const setWidescreenClass = (enabled: boolean) => {
    document.documentElement.classList.toggle('video-widescreen', !!enabled)
  }

  const syncWidescreenSidebarState = (enabled: boolean) => {
    uiStore.setVideoWidescreen(!!enabled)
  }

  const toggleWidescreen = (value: boolean) => {
    isWidescreen.value = value
    setWidescreenClass(isWidescreen.value)
    syncWidescreenSidebarState(isWidescreen.value)
  }

  const focusVideoPlayer = async () => {
    try {
      await focusGlobalVideoPlayer()
    } catch (error) {
      Logger.debug('Failed to focus video player', error)
    }
  }

  const isSameGlobalPlaybackSession = (videoId = route.params.videoId) => {
    return String(globalVideoPlayerSession.currentVideoId || '') === String(videoId || '')
  }

  const hasJavdbActors = (videoSnapshot: VideoPageVideo | null | undefined) => {
    const actors = videoSnapshot?.actors
    return Array.isArray(actors) && actors.some((actor) => String(actor?.name || '').trim())
  }

  const shouldRefreshJavdbSession = () => {
    const videoSnapshot = globalVideoPlayerSession.videoSnapshot || null
    const videoUrl = String(videoSnapshot?.url || '')
    if (!videoUrl.includes('javdb.com/')) return false
    return !hasJavdbActors(videoSnapshot)
  }

  const hasReusableGlobalPlaybackSession = (videoId = route.params.videoId) => {
    if (!isSameGlobalPlaybackSession(videoId)) return false
    if (shouldRefreshJavdbSession()) return false

    return !!(
      globalVideoPlayerSession.source
      || globalVideoPlayerSession.externalError
      || globalVideoPlayerSession.externalLoading
    )
  }

  const hydrateFromGlobalPlaybackSession = () => {
    hydratePlaybackState({
      videoSnapshot: globalVideoPlayerSession.videoSnapshot || null,
      nextPlaybackSource: globalVideoPlayerSession.source || null,
      nextSubtitleTracks: globalVideoPlayerSession.subtitles || [],
      nextExternalError: globalVideoPlayerSession.externalError || null,
      nextIsResolvingPlayback: globalVideoPlayerSession.externalLoading,
      nextRelatedVideos: globalVideoPlayerSession.relatedVideos || [],
      nextLoadingRelated: globalVideoPlayerSession.loadingRelated,
    })
  }

  const hasActivePictureInPictureSession = () => {
    if (globalVideoPlayerSession.pictureInPicture) {
      return true
    }

    if (typeof document === 'undefined') {
      return false
    }

    return !!document.pictureInPictureElement
  }

  watch(videoPlayerHostRef, (element) => {
    if (element) {
      registerGlobalVideoPlayerTarget(element)
      return
    }

    unregisterGlobalVideoPlayerTarget()
  }, { immediate: true })

  watch(
    [
      video,
      playbackSource,
      subtitleTracks,
      () => video.value?.title,
      resolvedInitialTime,
      clipMarkers,
      hasPrevVideo,
      hasNextVideo,
      externalError,
      isWidescreen,
      isResolvingPlayback,
      effectiveTheme,
      relatedVideos,
      loadingRelated,
      hasPrev,
      hasNext,
    ],
    ([
      nextVideo,
      nextSource,
      nextSubtitles,
      nextTitle,
      nextInitialTime,
      nextClipMarkers,
      nextHasPrev,
      nextHasNext,
      nextExternalError,
      nextWidescreen,
      nextExternalLoading,
      nextTheme,
      nextRelatedVideos,
      nextLoadingRelated,
      nextPlaylistPrev,
      nextPlaylistNext,
    ]) => {
      const primaryProfile: VideoProfile | null = Array.isArray(nextVideo?.subscriptions)
        ? nextVideo.subscriptions[0] || null
        : (Array.isArray(nextVideo?.actors) ? nextVideo.actors[0] || null : null)
      const nextUploader = String(
        primaryProfile?.name
        || nextVideo?.uploader
        || nextVideo?.uploader_name
        || ''
      )

      const hasLocalPlaybackState = !!(
        nextVideo
        || nextSource
        || nextExternalError
        || nextExternalLoading
      )

      if (!hasLocalPlaybackState && hasReusableGlobalPlaybackSession()) {
        return
      }

      activateGlobalVideoPlayerSession({
        target: videoPlayerHostRef.value,
        source: nextSource,
        subtitles: nextSubtitles || [],
        clipMarkers: nextClipMarkers || [],
        title: String(nextTitle || ''),
        uploader: nextUploader,
        initialTime: nextInitialTime,
        hasPrev: !!nextHasPrev,
        hasNext: !!nextHasNext,
        externalError: nextExternalError,
        widescreen: !!nextWidescreen,
        externalLoading: !!nextExternalLoading,
        adapter: playerAdapter,
        theme: nextTheme,
        currentVideoId: String(nextVideo?.id ?? route.params.videoId ?? ''),
        videoSnapshot: nextVideo || null,
        relatedVideos: nextRelatedVideos || [],
        loadingRelated: !!nextLoadingRelated,
        handlers: {
          onPlay: onVideoPlay,
          onPause: onVideoPause,
          onEnded: handleAutoplayNext,
          onTimeUpdate: handlePlaybackTimeUpdate,
          onPrev: nextPlaylistPrev ? handlePrevVideoFromPlaylist : null,
          onNext: nextPlaylistNext ? handleNextVideoFromPlaylist : null,
          onRetry: handlePlayerRetry,
          onWidescreenChange: toggleWidescreen,
          onClipMarkerSelect: handleClipMarkerSeek,
          onClipMarkersUpdated: handleClipMarkersUpdated,
        },
      })
    },
    { immediate: true },
  )

  onMounted(async () => {
    if (hasReusableGlobalPlaybackSession()) {
      hydrateFromGlobalPlaybackSession()
    } else {
        const videoId = String(route.params.videoId || '')
        await loadAndPlayById(videoId, consumePlaybackSeed(videoId))
    }
    await focusVideoPlayer()

    setWidescreenClass(isWidescreen.value)
    syncWidescreenSidebarState(isWidescreen.value)
  })

  watch(() => route.params.videoId, async (newId, oldId) => {
    if (newId && newId !== oldId && video.value?.id !== newId) {
      void flushPendingReport()
      if (hasReusableGlobalPlaybackSession(newId)) {
        hydrateFromGlobalPlaybackSession()
      } else {
        const videoId = String(newId || '')
        await loadAndPlayById(videoId, consumePlaybackSeed(videoId))
      }
      await focusVideoPlayer()
    }
  })

  onUnmounted(() => {
    setWidescreenClass(false)
    syncWidescreenSidebarState(false)
  unregisterGlobalVideoPlayerTarget()
    if (hasActivePictureInPictureSession()) {
      return
    }
    void flushPendingReport()
    clearGlobalVideoPlayerSession()
  })

  return {
    videoPlayerHostRef,
    videoPageRef,
    videoSectionRef,
    videoMetaRef,
    isWidescreen,
    toggleWidescreen,
    focusVideoPlayer,
    hasReusableGlobalPlaybackSession,
    hydrateFromGlobalPlaybackSession,
  }
}
