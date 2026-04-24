import { computed, ref } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import type { RouteLocationNormalizedLoaded, Router } from 'vue-router'

import { getRandomVideo } from '@/api'
import { rememberVideoPlaybackSeed } from './videoPlaybackSeed'

type VideoId = string | number

type VideoLike = {
  id?: VideoId
  title?: string
  thumbnail?: string
  [key: string]: unknown
}

type RouteLike = Pick<RouteLocationNormalizedLoaded, 'params'>

type GoToAdjacentVideo = () => VideoLike | null | undefined
type OnVideoEnded = () => void
type NavigateToVideo = (id: VideoId, videoData?: VideoLike | null) => Promise<void>

const RECENTLY_PLAYED_LIMIT = 5

export default function useVideoPageNavigation({
  route,
  router,
  video,
  relatedVideos,
  goToPrev,
  goToNext,
  onVideoEnded,
}: {
  route: RouteLike
  router: Router
  video: Ref<VideoLike | null>
  relatedVideos: Ref<VideoLike[]>
  goToPrev: GoToAdjacentVideo
  goToNext: GoToAdjacentVideo
  onVideoEnded: OnVideoEnded
}) {
  const recentlyPlayed = ref<VideoId[]>([])

  const pushRecentlyPlayed = (videoId: VideoId | null | undefined) => {
    if (videoId == null || recentlyPlayed.value.includes(videoId)) {
      return
    }

    recentlyPlayed.value.push(videoId)
    if (recentlyPlayed.value.length > RECENTLY_PLAYED_LIMIT) {
      recentlyPlayed.value.shift()
    }
  }

  const goToVideo: NavigateToVideo = async (id, videoData = null) => {
    if (id == null) return

    const targetId = String(id)
    if (String(video.value?.id ?? '') === targetId) return

    pushRecentlyPlayed(video.value?.id)
    if (videoData) {
      rememberVideoPlaybackSeed(videoData)
    }

    if (String(route.params.videoId ?? '') !== targetId) {
      const simpleState = videoData ? {
        videoId: videoData.id,
        title: videoData.title,
        thumbnail: videoData.thumbnail,
      } : {}

      try {
        await router.replace({ name: 'VideoPlay', params: { videoId: targetId }, query: {}, state: simpleState })
      } catch {
        await router.replace(`/video/${targetId}`)
      }
    }
  }

  const findNextUnplayedRelatedVideo = (direction: 'forward' | 'backward') => {
    const relatedList = Array.isArray(relatedVideos.value) ? relatedVideos.value : []
    if (!relatedList.length) {
      return null
    }

    const currentId = String(video.value?.id ?? route.params.videoId ?? '')
    const candidates = direction === 'backward' ? [...relatedList].reverse() : relatedList

    const preferred = candidates.find((item) => (
      item?.id != null
      && String(item.id) !== currentId
      && !recentlyPlayed.value.includes(item.id)
    ))
    if (preferred) {
      return preferred
    }

    return candidates.find((item) => item?.id != null && String(item.id) !== currentId) || null
  }

  const hasPrevVideo = computed(() => Array.isArray(relatedVideos.value) && relatedVideos.value.length > 0)
  const hasNextVideo = computed(() => Array.isArray(relatedVideos.value) && relatedVideos.value.length > 0)

  const handlePrevVideo = async () => {
    const previousVideo = findNextUnplayedRelatedVideo('backward')
    if (previousVideo?.id != null) {
      await goToVideo(previousVideo.id, previousVideo)
    }
  }

  const handleNextVideo = async () => {
    const nextVideo = findNextUnplayedRelatedVideo('forward')
    if (nextVideo?.id != null) {
      await goToVideo(nextVideo.id, nextVideo)
    }
  }

  const handlePrevVideoFromPlaylist = async () => {
    const previousVideo = goToPrev()
    if (previousVideo?.id != null) {
      await goToVideo(previousVideo.id, previousVideo)
      return
    }

    await handlePrevVideo()
  }

  const handleNextVideoFromPlaylist = async () => {
    const nextVideo = goToNext()
    if (nextVideo?.id != null) {
      await goToVideo(nextVideo.id, nextVideo)
      return
    }

    await handleNextVideo()
  }

  const handleAutoplayNext = async (event?: { autoplay?: boolean; autoplayNext?: boolean; loop?: boolean }) => {
    try {
      onVideoEnded()

      const autoplayEnabled = event?.autoplay ?? true
      const autoplayNextEnabled = event?.autoplayNext ?? true
      const loopEnabled = event?.loop ?? false
      if (!autoplayEnabled || !autoplayNextEnabled || loopEnabled) {
        return
      }

      const nextPlaylistVideo = goToNext()
      if (nextPlaylistVideo?.id != null) {
        await goToVideo(nextPlaylistVideo.id, nextPlaylistVideo)
        return
      }

      await handleNextVideo()
    } catch {
      // Ignore autoplay navigation failures.
    }
  }

  const handlePlayRandom = async () => {
    const maxAttempts = 3

    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      const response = await getRandomVideo({})
      if (!response.error && response.data?.id != null && !recentlyPlayed.value.includes(response.data.id)) {
        await goToVideo(response.data.id, response.data)
        return
      }
    }

    const fallbackResponse = await getRandomVideo({})
    if (!fallbackResponse.error && fallbackResponse.data?.id != null) {
      await goToVideo(fallbackResponse.data.id, fallbackResponse.data)
    }
  }

  return {
    goToVideo,
    hasPrevVideo,
    hasNextVideo,
    handlePrevVideo,
    handleNextVideo,
    handlePrevVideoFromPlaylist,
    handleNextVideoFromPlaylist,
    handleAutoplayNext,
    handlePlayRandom,
    recentlyPlayed: computed(() => recentlyPlayed.value),
  }
}
