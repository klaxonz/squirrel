import { computed } from 'vue'

import { getVideoDetail } from '@/shared/api'
import type { VideoId, VideoPageVideo, VideoSubtitle } from '@/features/playback/types/videoPlayback'
import { Logger } from '@/shared/lib/logger'
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'
import { consumePendingPosition } from '@/features/playback/composables/playbackPositionBuffer'
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

  const fetchVideoDetails = async (videoId: VideoId, timeoutMs = 15000) => {
    const seq = ++detailRequestSeq
    let timeout: ReturnType<typeof setTimeout> | null = null

    try {
      const data = await Promise.race([
        getVideoDetail(videoId) as Promise<VideoPageVideo | null>,
        new Promise<never>((_, reject) => {
          timeout = setTimeout(() => {
            reject(Object.assign(new Error('视频信息加载超时，请重试'), { code: 'METADATA_TIMEOUT' }))
          }, timeoutMs)
        }),
      ])
      if (!data) throw new Error('未找到视频信息')
      if (seq === detailRequestSeq) {
        // 卸载时 flush 的上报可能还没落地：合并本地乐观位置，避免"返回后
        // 立即重开"续播到旧进度。合并值只可能比服务器值新（本地观测时间
        // 更晚），服务器随后落地时也是同一数值。
        const pendingPosition = consumePendingPosition(String(data.id))
        const merged = pendingPosition != null
          ? { ...data, last_position: Math.max(Number(data.last_position) || 0, pendingPosition) }
          : data

        // 会话可能已在请求期间被释放（用户返回视频库 / 切换到其它视频）——
        // 迟到响应不得把旧视频写回已清空的全局会话。videoId 匹配本身由
        // detailRequestSeq 守卫，但 release() 不清 seq，这里必须显式复核。
        if (String(session.facts.videoId || '') === String(videoId)) {
          session.update({ video: merged })
        }
        return merged
      }
      return data
    } catch (error) {
      // Invalidate the unresolved request after a timeout so a late response
      // cannot overwrite a newer route or retry result.
      if (seq === detailRequestSeq) detailRequestSeq += 1
      throw error
    } finally {
      if (timeout) clearTimeout(timeout)
    }
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
