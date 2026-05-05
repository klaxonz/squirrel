import { computed, ref } from 'vue'
import { getVideoDetail } from '@/api'
import type { VideoClipMarker } from '@/types/videoClipMarker'

type VideoId = string | number

type VideoSubtitle = {
  id: string
  label?: string
  language: string
  url: string
  content?: string
  default?: boolean
}

type VideoLike = {
  id: VideoId
  url?: string
  duration?: number
  last_position?: number
  subtitles?: VideoSubtitle[]
  clip_markers?: VideoClipMarker[]
  [key: string]: unknown
}

type SubtitleCandidate = {
  id: string
  language: string
  lang?: string
}

const subtitleCandidatesByDomain: Array<{ pattern: RegExp; candidates: SubtitleCandidate[] }> = [
  {
    pattern: /bilibili\.com/i,
    candidates: [
      { id: 'bili-ai-zh', language: '简体中文（自动）', lang: 'ai-zh' },
      { id: 'bili-zh-CN', language: '简体中文', lang: 'zh-CN' },
      { id: 'bili-zh', language: '中文', lang: 'zh' },
    ],
  },
  {
    pattern: /(?:youtube\.com|youtu\.be)/i,
    candidates: [
      { id: 'yt-default', language: '默认' },
      { id: 'yt-en', language: '英语', lang: 'en' },
      { id: 'yt-en-US', language: '美式英语', lang: 'en-US' },
    ],
  },
]

const getSubtitleCandidates = (url: string | undefined): SubtitleCandidate[] => {
  if (!url) return []
  return subtitleCandidatesByDomain.find(({ pattern }) => pattern.test(url))?.candidates || []
}

export default function useVideoDetail(initialVideo: VideoLike | null = null) {
  const video = ref<VideoLike | null>(initialVideo)
  let detailRequestSeq = 0

  const replaceVideo = (nextVideo: VideoLike | null) => {
    video.value = nextVideo
  }

  const setVideoSnapshot = (nextVideo: VideoLike | null) => {
    detailRequestSeq += 1
    replaceVideo(nextVideo)
  }

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
    const seq = ++detailRequestSeq
    const { data, error } = (await getVideoDetail(videoId)) as { data?: VideoLike | null; error?: unknown | null }
    if (!error && seq === detailRequestSeq) {
      replaceVideo(data || null)
    }
    return video.value
  }

  const maybeInjectSubtitles = async (videoId: VideoId) => {
    const snapshot = video.value
    if (!snapshot || String(snapshot.id) !== String(videoId)) return

    const candidates = getSubtitleCandidates(snapshot.url)
    if (!candidates.length) return

    const existingSubtitles = Array.isArray(snapshot.subtitles) ? snapshot.subtitles : []
    const subtitlePlaceholders = candidates
      .filter((candidate) => !existingSubtitles.some((subtitle) => subtitle.id === candidate.id))
      .map((candidate, index) => {
        const params = new URLSearchParams({
          video_id: String(videoId),
          fmt: /(?:youtube\.com|youtu\.be)/i.test(snapshot.url || '') ? 'vtt' : 'srt',
        })
        if (candidate.lang) {
          params.set('lang', candidate.lang)
        }

        return {
          id: candidate.id,
          label: candidate.language,
          language: candidate.language,
          url: `/api/video/subtitles?${params.toString()}`,
          default: index === 0,
        } satisfies VideoSubtitle
      })

    if (!subtitlePlaceholders.length) return
    snapshot.subtitles = [...existingSubtitles, ...subtitlePlaceholders]
  }

  return {
    video,
    startTime,
    fetchVideoDetails,
    maybeInjectSubtitles,
    setVideoSnapshot,
  }
}
