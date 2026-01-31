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

  const maybeResetForNewVideo = () => {
    const currentId = videoRef.value?.id ?? null
    if (currentId !== lastVideoId) {
      lastVideoId = currentId
      lastReportedTime = 0
    }
  }

  const onVideoPlay = () => {
    maybeResetForNewVideo()
    if (videoRef.value) videoRef.value.isPlaying = true
  }

  const onVideoPause = () => {
    if (videoRef.value) videoRef.value.isPlaying = false
  }

  const onVideoEnded = () => {
    if (videoRef.value) videoRef.value.if_read = true
  }

  const onVideoTimeUpdate = (currentTime: number) => {
    maybeResetForNewVideo()
    if (!videoRef.value) return
    if (Math.floor(currentTime) - lastReportedTime < 2) return

    lastReportedTime = Math.floor(currentTime)
    videoRef.value.last_position = currentTime
    const total = Number(videoRef.value.duration) || 0
    videoRef.value.progress = total > 0 ? (currentTime / total) * 100 : 0

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


