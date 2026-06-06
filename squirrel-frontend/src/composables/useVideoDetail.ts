import { computed, ref } from 'vue'
import { getVideoDetail } from '@/api'
import type { VideoId, VideoPageVideo, VideoSubtitle } from '@/types/videoPlayback'

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

const isYouTubeUrl = (url: string | undefined) => /(?:youtube\.com|youtu\.be)/i.test(url || '')

const getDesktopBridge = () => {
  if (typeof window === 'undefined') return null
  return window.desktopApp || null
}

const buildDesktopYouTubeSubtitleTracks = async (
  videoUrl: string,
  candidates: SubtitleCandidate[],
): Promise<VideoSubtitle[]> => {
  const bridge = getDesktopBridge()
  if (bridge?.isDesktop !== true || typeof bridge.resolveYouTubeSubtitles !== 'function') {
    return []
  }

  const tracks: VideoSubtitle[] = []
  for (const [index, candidate] of candidates.entries()) {
    try {
      const payload = await bridge.resolveYouTubeSubtitles(videoUrl, {
        lang: candidate.lang,
        format: 'vtt',
      })
      const content = String(payload?.content || '').trim()
      if (!content) continue

      tracks.push({
        id: candidate.id,
        label: candidate.language,
        language: candidate.language,
        content,
        default: index === 0,
      })
    } catch {
      // Skip unavailable desktop subtitle tracks.
    }
  }
  return tracks
}

const canResolveDesktopYouTubeSubtitles = () => {
  const bridge = getDesktopBridge()
  return bridge?.isDesktop === true && typeof bridge.resolveYouTubeSubtitles === 'function'
}

export default function useVideoDetail(initialVideo: VideoPageVideo | null = null) {
  const video = ref<VideoPageVideo | null>(initialVideo)
  let detailRequestSeq = 0

  const replaceVideo = (nextVideo: VideoPageVideo | null) => {
    video.value = nextVideo
  }

  const setVideoSnapshot = (nextVideo: VideoPageVideo | null) => {
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
    const { data, error } = (await getVideoDetail(videoId)) as { data?: VideoPageVideo | null; error?: unknown | null }
    if (!error && seq === detailRequestSeq) {
      replaceVideo(data || null)
    }
    return video.value
  }

  const maybeInjectSubtitles = async (videoId: VideoId) => {
    const snapshot = video.value
    if (!snapshot || String(snapshot.id) !== String(videoId)) return

    const snapshotUrl = snapshot.url || undefined
    const candidates = getSubtitleCandidates(snapshotUrl)
    if (!candidates.length) return

    const existingSubtitles = Array.isArray(snapshot.subtitles) ? snapshot.subtitles : []
    const missingCandidates = candidates
      .filter((candidate) => !existingSubtitles.some((subtitle) => subtitle.id === candidate.id))

    if (isYouTubeUrl(snapshotUrl) && canResolveDesktopYouTubeSubtitles()) {
      const desktopTracks = await buildDesktopYouTubeSubtitleTracks(snapshotUrl || '', missingCandidates)
      if (!desktopTracks.length) return
      snapshot.subtitles = [...existingSubtitles, ...desktopTracks]
      return
    }

    const subtitlePlaceholders = missingCandidates
      .map((candidate, index) => {
        const params = new URLSearchParams({
          video_id: String(videoId),
          fmt: isYouTubeUrl(snapshotUrl) ? 'vtt' : 'srt',
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
