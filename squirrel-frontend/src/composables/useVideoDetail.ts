import { computed, onScopeDispose, ref } from 'vue'
import { getVideoDetail, getVideoSubtitles } from '@/api'

type VideoId = string | number

type VideoSubtitle = {
  id: string
  language: string
  url: string
}

type VideoLike = {
  id: VideoId
  url?: string
  duration?: number
  last_position?: number
  subtitles?: VideoSubtitle[]
  [key: string]: unknown
}

type ApiResult<T> = { data?: T | null; error?: unknown | null }

type SubtitleCandidate = {
  id: string
  language: string
  lang?: string
}

const subtitleCandidatesByDomain: Array<{ pattern: RegExp; candidates: SubtitleCandidate[] }> = [
  {
    pattern: /bilibili\.com/i,
    candidates: [
      { id: 'bili-ai-zh', language: '简体中文(AI)', lang: 'ai-zh' },
      { id: 'bili-zh-CN', language: '简体中文', lang: 'zh-CN' },
      { id: 'bili-zh', language: '中文', lang: 'zh' },
    ],
  },
  {
    pattern: /(?:youtube\.com|youtu\.be)/i,
    candidates: [
      { id: 'yt-en', language: 'English', lang: 'en' },
      { id: 'yt-en-US', language: 'English (US)', lang: 'en-US' },
    ],
  },
]

const getSubtitleCandidates = (url: string | undefined): SubtitleCandidate[] => {
  if (!url) return []
  return subtitleCandidatesByDomain.find(({ pattern }) => pattern.test(url))?.candidates || []
}

export default function useVideoDetail(initialVideo: VideoLike | null = null) {
  const video = ref<VideoLike | null>(initialVideo)
  const managedSubtitleObjectUrls = new Set<string>()
  let detailRequestSeq = 0

  const revokeManagedSubtitleObjectUrls = () => {
    managedSubtitleObjectUrls.forEach((url) => {
      URL.revokeObjectURL(url)
    })
    managedSubtitleObjectUrls.clear()
  }

  const replaceVideo = (nextVideo: VideoLike | null) => {
    revokeManagedSubtitleObjectUrls()
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
    const { data, error } = (await getVideoDetail(videoId)) as ApiResult<VideoLike>
    if (!error && seq === detailRequestSeq) {
      replaceVideo(data || null)
    }
    return video.value
  }

  const maybeInjectSubtitles = async (videoId: VideoId) => {
    const seq = detailRequestSeq
    const snapshot = video.value
    if (!snapshot || String(snapshot.id) !== String(videoId)) return

    const candidates = getSubtitleCandidates(snapshot.url)
    if (!candidates.length) return

    for (const candidate of candidates) {
      const currentVideo = video.value
      if (!currentVideo || String(currentVideo.id) !== String(videoId)) return

      const existingSubtitles = Array.isArray(currentVideo.subtitles) ? currentVideo.subtitles : []
      if (existingSubtitles.some((subtitle) => subtitle.id === candidate.id || subtitle.language === candidate.language)) {
        return
      }

      const { data, error } = (await getVideoSubtitles(videoId, { lang: candidate.lang, fmt: 'srt' })) as ApiResult<string>
      if (error || typeof data !== 'string' || data.length === 0) continue
      if (seq !== detailRequestSeq || !video.value || String(video.value.id) !== String(videoId)) return

      const blob = new Blob([data], { type: 'text/plain;charset=utf-8' })
      const objectUrl = URL.createObjectURL(blob)
      managedSubtitleObjectUrls.add(objectUrl)
      const subtitle: VideoSubtitle = {
        id: candidate.id,
        language: candidate.language,
        url: objectUrl,
      }

      if (seq !== detailRequestSeq || !video.value || String(video.value.id) !== String(videoId)) {
        managedSubtitleObjectUrls.delete(objectUrl)
        URL.revokeObjectURL(objectUrl)
        return
      }

      video.value.subtitles = [subtitle, ...existingSubtitles]
      return
    }
  }

  onScopeDispose(() => {
    revokeManagedSubtitleObjectUrls()
  })

  return {
    video,
    startTime,
    fetchVideoDetails,
    maybeInjectSubtitles,
    setVideoSnapshot,
  }
}
