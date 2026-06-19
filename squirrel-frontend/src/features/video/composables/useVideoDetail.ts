import { computed } from 'vue'

import { getVideoDetail } from '@/shared/api'
import type { VideoId, VideoPageVideo, VideoSubtitle } from '@/features/playback/types/videoPlayback'
import { Logger } from '@/shared/lib/logger'
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'
import type { PlaybackSession } from '@/features/playback/composables/usePlaybackSession'

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

const desktopBridge = useDesktopBridge()

const buildDesktopYouTubeSubtitleTracks = async (
  videoUrl: string,
  candidates: SubtitleCandidate[],
): Promise<VideoSubtitle[]> => {
  if (!desktopBridge.isDesktop()) return []

  const tracks: VideoSubtitle[] = []
  for (const [index, candidate] of candidates.entries()) {
    try {
      const promise = desktopBridge.resolveYouTubeSubtitles(videoUrl, { lang: candidate.lang, format: 'vtt' })
      if (!promise) continue
      const payload = await promise
      const content = String(payload?.content || '').trim()
      if (!content) continue

      tracks.push({
        id: candidate.id,
        label: candidate.language,
        language: candidate.language,
        content,
        default: index === 0,
      })
    } catch (err) {
      Logger.warn('[useVideoDetail] Failed to resolve YouTube subtitle track', err)
    }
  }
  return tracks
}

const canResolveDesktopYouTubeSubtitles = () => {
  return desktopBridge.isDesktop() && !!desktopBridge.getDesktopBridge()?.resolveYouTubeSubtitles
}

const canResolveDesktopBilibiliSubtitles = () => {
  return desktopBridge.isDesktop() && !!desktopBridge.getDesktopBridge()?.resolveBilibiliSubtitles
}

const buildDesktopBilibiliSubtitleTracks = async (
  videoUrl: string,
  candidates: SubtitleCandidate[],
): Promise<VideoSubtitle[]> => {
  if (!desktopBridge.isDesktop()) return []

  const tracks: VideoSubtitle[] = []
  for (const [index, candidate] of candidates.entries()) {
    try {
      const promise = desktopBridge.resolveBilibiliSubtitles(videoUrl, { lang: candidate.lang })
      if (!promise) continue
      const payload = await promise
      const content = String(payload?.content || '').trim()
      if (!content) continue

      tracks.push({
        id: candidate.id,
        label: candidate.language,
        language: candidate.language,
        content,
        default: index === 0,
      })
    } catch (err) {
      Logger.warn('[useVideoDetail] Failed to resolve Bilibili subtitle track', err)
    }
  }
  return tracks
}

// ADR-0002 PR2 — `video` used to be a local ref() owned here. It is
// now a read-only projection of PlaybackSession.facts.video (the single owner).
// All mutations route through session.update({ video }) so the reactive object
// identity stays stable for consumers that read nested fields (clip markers,
// subtitles). The seed that used to be the constructor arg is gone — the shell
// hands the seed to session.beginNewVideo(id, seed), which seeds facts.video
// before fetchVideoDetails runs.
export default function useVideoDetail(session: PlaybackSession) {
  const video = computed(() => session.facts.video)
  let detailRequestSeq = 0

  const setVideoSnapshot = (nextVideo: VideoPageVideo | null) => {
    detailRequestSeq += 1
    session.update({ video: nextVideo })
  }

  const startTime = computed(() => {
    const lastPosition = session.facts.video?.last_position
    if (!lastPosition) return 0

    const total = Number(session.facts.video?.duration) || 0
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
      session.update({ video: data || null })
    }
    return session.facts.video
  }

  const maybeInjectSubtitles = async (videoId: VideoId) => {
    const snapshot = session.facts.video
    if (!snapshot || String(snapshot.id) !== String(videoId)) return

    const snapshotUrl = snapshot.url || undefined
    const candidates = getSubtitleCandidates(snapshotUrl)
    if (!candidates.length) return

    const existingSubtitles = Array.isArray(snapshot.subtitles) ? snapshot.subtitles : []
    const missingCandidates = candidates
      .filter((candidate) => !existingSubtitles.some((subtitle) => subtitle.id === candidate.id))

    let nextTracks: VideoSubtitle[] | null = null

    if (isYouTubeUrl(snapshotUrl) && canResolveDesktopYouTubeSubtitles()) {
      const desktopTracks = await buildDesktopYouTubeSubtitleTracks(snapshotUrl || '', missingCandidates)
      if (!desktopTracks.length) return
      nextTracks = [...existingSubtitles, ...desktopTracks]
    } else if (canResolveDesktopBilibiliSubtitles()) {
      const desktopTracks = await buildDesktopBilibiliSubtitleTracks(snapshotUrl || '', missingCandidates)
      if (!desktopTracks.length) return
      nextTracks = [...existingSubtitles, ...desktopTracks]
    }

    if (!nextTracks) return

    // Re-check after the awaits: the session video may have switched underneath us.
    const current = session.facts.video
    if (!current || String(current.id) !== String(videoId)) return

    session.update({ video: { ...current, subtitles: nextTracks } })
  }

  return {
    video,
    startTime,
    fetchVideoDetails,
    maybeInjectSubtitles,
    setVideoSnapshot,
  }
}
