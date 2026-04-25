import { onMounted, onUnmounted, ref, watch } from 'vue'
import type { Ref } from 'vue'

import { Logger } from '@/utils/logger'

type VideoId = string | number

type VideoLike = {
  id?: VideoId
  title?: string
  [key: string]: unknown
}

type PlaybackSourceLike = Record<string, unknown> | null
type ClipMarkerLike = Record<string, unknown>
type RelatedVideoLike = Record<string, unknown>
type VideoSeedGetter = (videoId: unknown) => VideoLike | null

type RouteLike = {
  params: Record<string, unknown>
}

type GlobalPlaybackSessionLike = {
  currentVideoId?: string | number | null
  source?: PlaybackSourceLike
  externalError?: unknown
  externalLoading?: boolean
  videoSnapshot?: VideoLike | null
  subtitles?: unknown[]
  relatedVideos?: RelatedVideoLike[]
  loadingRelated?: boolean
  pictureInPicture?: boolean
}

type ActivateSessionPayload = {
  target: HTMLElement | null
  source: PlaybackSourceLike
  subtitles: unknown[]
  clipMarkers: ClipMarkerLike[]
  title: string
  initialTime: number | null | undefined
  hasPrev: boolean
  hasNext: boolean
  externalError: unknown
  widescreen: boolean
  externalLoading: boolean
  adapter: unknown
  theme: unknown
  currentVideoId: string
  videoSnapshot: VideoLike | null
  relatedVideos: RelatedVideoLike[]
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
    onClipMarkersUpdated: ((markers: ClipMarkerLike[]) => void) | null
  }
}

export default function useVideoPlaybackShell({
  route,
  emitter,
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
  emitter?: { emit: (event: string, payload: unknown) => void } | null
  playerAdapter: unknown
  video: Ref<VideoLike | null>
  playbackSource: Ref<PlaybackSourceLike>
  subtitleTracks: Ref<unknown[]>
  resolvedInitialTime: Ref<number | null | undefined>
  clipMarkers: Ref<ClipMarkerLike[]>
  hasPrevVideo: Ref<boolean>
  hasNextVideo: Ref<boolean>
  externalError: Ref<unknown>
  isResolvingPlayback: Ref<boolean>
  effectiveTheme: Ref<unknown>
  relatedVideos: Ref<RelatedVideoLike[]>
  loadingRelated: Ref<boolean>
  hasPrev: Ref<boolean>
  hasNext: Ref<boolean>
  globalVideoPlayerSession: GlobalPlaybackSessionLike
  activateGlobalVideoPlayerSession: (payload: ActivateSessionPayload) => void
  clearGlobalVideoPlayerSession: () => void
  registerGlobalVideoPlayerTarget: (target: HTMLElement) => void
  unregisterGlobalVideoPlayerTarget: (target?: HTMLElement | null) => void
  focusGlobalVideoPlayer: () => Promise<void>
  hydratePlaybackState: (payload: {
    videoSnapshot: VideoLike | null
    nextPlaybackSource: PlaybackSourceLike
    nextSubtitleTracks: unknown[]
    nextExternalError: unknown
    nextIsResolvingPlayback: boolean | undefined
    nextRelatedVideos: RelatedVideoLike[]
    nextLoadingRelated: boolean | undefined
  }) => void
  loadAndPlayById: (videoId: unknown, initialVideoData?: VideoLike | null) => Promise<void>
  consumePlaybackSeed: VideoSeedGetter
  onVideoPlay: () => void
  onVideoPause: () => void
  handleAutoplayNext: (event?: { autoplay?: boolean; autoplayNext?: boolean; loop?: boolean }) => void | Promise<void>
  handlePlaybackTimeUpdate: (currentTime: number) => void
  handlePrevVideoFromPlaylist: () => void | Promise<void>
  handleNextVideoFromPlaylist: () => void | Promise<void>
  handlePlayerRetry: () => void | Promise<void>
  handleClipMarkerSeek: (time: number) => void | Promise<void>
  handleClipMarkersUpdated: (markers: ClipMarkerLike[]) => void
  flushPendingReport: () => Promise<void>
}) {
  const videoPlayerHostRef = ref<HTMLElement | null>(null)
  const videoPageRef = ref<HTMLElement | null>(null)
  const videoSectionRef = ref<HTMLElement | null>(null)
  const videoMetaRef = ref<HTMLElement | null>(null)
  const isWidescreen = ref(false)

  const setWidescreenClass = (enabled: boolean) => {
    document.documentElement.classList.toggle('video-widescreen', !!enabled)
  }

  const syncWidescreenSidebarState = (enabled: boolean) => {
    if (!emitter) return
    emitter.emit('videoWidescreenStateChanged', !!enabled)
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

  const hasReusableGlobalPlaybackSession = (videoId = route.params.videoId) => {
    if (!isSameGlobalPlaybackSession(videoId)) return false

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
      await loadAndPlayById(route.params.videoId, consumePlaybackSeed(route.params.videoId))
    }
    await focusVideoPlayer()

    setWidescreenClass(isWidescreen.value)
    syncWidescreenSidebarState(isWidescreen.value)
  })

  watch(() => route.params.videoId, async (newId, oldId) => {
    if (newId && newId !== oldId && video.value?.id !== newId) {
      if (hasReusableGlobalPlaybackSession(newId)) {
        hydrateFromGlobalPlaybackSession()
      } else {
        await loadAndPlayById(newId, consumePlaybackSeed(newId))
      }
      await focusVideoPlayer()
    }
  })

  onUnmounted(() => {
    setWidescreenClass(false)
    syncWidescreenSidebarState(false)
    unregisterGlobalVideoPlayerTarget(videoPlayerHostRef.value)
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
