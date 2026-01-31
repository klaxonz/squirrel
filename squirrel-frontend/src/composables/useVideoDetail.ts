import { computed, ref } from 'vue'
import { getVideoDetail, getVideoSubtitles } from '@/api'

type VideoId = string | number

type VideoSubtitle = {
  id: string
  language: string
  url: string
}

type VideoLike = {
  id?: VideoId
  url?: string
  duration?: number
  last_position?: number
  subtitles?: VideoSubtitle[]
  [key: string]: unknown
}

type ApiResult<T> = { data?: T | null; error?: unknown | null }

export default function useVideoDetail(initialVideo: VideoLike | null = null) {
  const video = ref<VideoLike | null>(initialVideo)

  const startTime = computed(() => {
    const lastPosition = video.value?.last_position
    if (!lastPosition) return 0

    const total = Number(video.value?.duration) || 0
    if (!total || total <= 0 || lastPosition <= 0) return 0

    const progress = (lastPosition / total) * 100
    const remainingTime = total - lastPosition

    let isNearEnd = false
    if (total < 300) {
      isNearEnd = progress >= 85
    } else if (total < 1800) {
      isNearEnd = progress >= 90 || remainingTime < 120
    } else {
      isNearEnd = progress >= 95 || remainingTime < 180
    }
    return isNearEnd ? 0 : lastPosition
  })

  const fetchVideoDetails = async (videoId: VideoId) => {
    const { data, error } = (await getVideoDetail(videoId)) as ApiResult<VideoLike>
    if (!error) video.value = data || null
    return video.value
  }

  const maybeInjectSubtitles = async (videoId: VideoId) => {
    const url = video.value?.url
    if (!url || !/bilibili\.com/.test(url)) return

    const { data, error } = (await getVideoSubtitles(videoId, { lang: 'ai-zh', fmt: 'srt' })) as ApiResult<string>
    if (error || typeof data !== 'string' || data.length === 0) return

    const blob = new Blob([data], { type: 'text/plain;charset=utf-8' })
    const objectUrl = URL.createObjectURL(blob)
    const subtitle: VideoSubtitle = { id: 'bili-ai-zh', language: '简体中文(AI)', url: objectUrl }

    if (!video.value) return
    video.value.subtitles = [subtitle, ...(video.value.subtitles || [])]
  }

  return {
    video,
    startTime,
    fetchVideoDetails,
    maybeInjectSubtitles,
  }
}


