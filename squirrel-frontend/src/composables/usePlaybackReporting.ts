import type { Ref } from 'vue'

type VideoId = string | number

type VideoLike = {
  id: VideoId
  isPlaying?: boolean
  if_read?: boolean
  is_read?: boolean
  last_position?: number
  duration?: number
  progress?: number
  [key: string]: unknown
}

type SendReport = (videoId: VideoId, currentTime: number) => Promise<unknown>

export default function usePlaybackReporting(videoRef: Ref<VideoLike | null>, sendReport: SendReport) {
  let lastVideoId: VideoId | null = null
  let lastReportedTime = 0
  let lastObservedTime = 0

  const maybeResetForNewVideo = () => {
    const currentId = videoRef.value?.id ?? null
    if (currentId !== lastVideoId) {
      lastVideoId = currentId
      lastReportedTime = 0
      lastObservedTime = 0
    }
  }

  const syncLocalPlaybackPosition = (currentTime = lastObservedTime) => {
    const nextTime = Number(currentTime)
    if (!videoRef.value || !Number.isFinite(nextTime) || nextTime < 0) return
    videoRef.value.last_position = nextTime
  }

  const onVideoPlay = () => {
    maybeResetForNewVideo()
    if (videoRef.value) videoRef.value.isPlaying = true
  }

  const onVideoPause = () => {
    if (videoRef.value) videoRef.value.isPlaying = false
    syncLocalPlaybackPosition()
  }

  const onVideoEnded = () => {
    const duration = Number(videoRef.value?.duration) || lastObservedTime
    syncLocalPlaybackPosition(duration)
    if (videoRef.value) videoRef.value.if_read = true
  }

  const onVideoTimeUpdate = (currentTime: number) => {
    maybeResetForNewVideo()
    if (!videoRef.value) return
    lastObservedTime = currentTime
    if (Math.floor(currentTime) - lastReportedTime < 2) return

    lastReportedTime = Math.floor(currentTime)

    ;(async () => {
      try {
        await sendReport(videoRef.value!.id, currentTime)
      } catch (_) {}
    })()
  }

  return {
    onVideoPlay,
    onVideoPause,
    onVideoEnded,
    onVideoTimeUpdate,
  }
}


