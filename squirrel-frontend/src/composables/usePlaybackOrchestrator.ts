import { computed, watch } from 'vue'

import useVideoDetail from './useVideoDetail'
import useRelatedVideos from './useRelatedVideos'
import useVideoOperations from './useVideoOperations'
import { usePlaybackSession } from './usePlaybackSession'
import { Logger } from '@/utils/logger'
import type { MediaSource } from '@/components/video-player/core'
import type { SubtitleTrack } from '@/components/video-player/plugins/subtitles'
import type { VideoId, VideoPageVideo, VideoProfile } from '@/types/videoPlayback'
import type { ExternalErrorState } from '@/types/playerSession'

export type { ExternalErrorState }

type PlayOptions = Record<string, unknown>

const toRecord = (value: unknown): Record<string, unknown> => {
  if (value && typeof value === 'object') return value as Record<string, unknown>
  return {}
}

const actorKey = (actor: VideoProfile) => {
  const url = String(actor.url || '').trim().toLowerCase()
  if (url) return `url:${url}`
  const id = String(actor.id || '').trim()
  if (id) return `id:${id}`
  const name = String(actor.name || '').trim().toLowerCase()
  return name ? `name:${name}` : ''
}

const mergeActor = (currentActor: VideoProfile, nextActor: VideoProfile) => {
  const merged: Record<string, unknown> = { ...currentActor }
  for (const [key, value] of Object.entries(nextActor)) {
    if (value != null && value !== '' && (merged[key] == null || merged[key] === '')) {
      merged[key] = value
    }
  }
  return merged as VideoProfile
}

const mergeActors = (currentActors: unknown, nextActors: VideoProfile[]) => {
  const mergedActors = Array.isArray(currentActors)
    ? currentActors.map((actor) => ({ ...toRecord(actor) } as VideoProfile))
    : []
  const indexByKey = new Map<string, number>()

  mergedActors.forEach((actor, index) => {
    const key = actorKey(actor)
    if (key) indexByKey.set(key, index)
  })

  for (const actor of nextActors) {
    const key = actorKey(actor)
    const existingIndex = key ? indexByKey.get(key) : undefined
    if (existingIndex != null) {
      mergedActors[existingIndex] = mergeActor(mergedActors[existingIndex], actor)
      continue
    }
    mergedActors.push(actor)
    if (key) indexByKey.set(key, mergedActors.length - 1)
  }

  return mergedActors
}

export const mergeVideoMetadata = (currentVideo: VideoPageVideo | null, videoMetadata: Record<string, unknown>, sourceUrl = '') => {
  if (!currentVideo || !videoMetadata || Object.keys(videoMetadata).length === 0) return currentVideo

  const currentUrl = String(currentVideo.url || '')
  if (sourceUrl && currentUrl && sourceUrl !== currentUrl) return currentVideo

  const nextVideo: VideoPageVideo = { ...currentVideo }
  if (typeof videoMetadata.title === 'string' && videoMetadata.title) {
    nextVideo.title = videoMetadata.title
  }
  if (typeof videoMetadata.thumbnail === 'string' && videoMetadata.thumbnail) {
    nextVideo.thumbnail = videoMetadata.thumbnail
  }
  if (typeof videoMetadata.publish_date === 'string' && videoMetadata.publish_date) {
    nextVideo.publish_date = videoMetadata.publish_date
  }
  if (typeof videoMetadata.duration === 'number') {
    nextVideo.duration = videoMetadata.duration
  }

  if (Array.isArray(videoMetadata.actors) && videoMetadata.actors.length > 0) {
    nextVideo.actors = mergeActors(nextVideo.actors, videoMetadata.actors.map((actor) => toRecord(actor) as VideoProfile))
  }

  if (Array.isArray(videoMetadata.subscriptions) && videoMetadata.subscriptions.length > 0) {
    nextVideo.subscriptions = mergeActors(nextVideo.subscriptions, videoMetadata.subscriptions.map((subscription) => toRecord(subscription) as VideoProfile))
  }

  return nextVideo
}

const mergePlaybackMetadata = (currentVideo: VideoPageVideo | null, playbackMetadata: Record<string, unknown>) => {
  return mergeVideoMetadata(currentVideo, toRecord(playbackMetadata.video), String(playbackMetadata.source_url || ''))
}

// ADR-0002 PR2 — the data-flow inversion. The 7 local refs that used
// to duplicate session facts (video / playbackSource / subtitleTracks /
// externalError / isResolvingPlayback / relatedVideos / loadingRelated) are now
// read-only `computed` projections of PlaybackSession.facts. There is no second
// copy of the facts for the shell's watcher to reconcile — that watcher is
// deleted in PR2. Mutation happens once, at the fetch/mutation sites, through
// session.update() / session.beginNewVideo().
//
// The `title` / `uploader` presentation facts, previously derived inside the
// shell's watcher body, are derived here from the session video and forwarded
// to facts whenever the video identity changes.
type DesktopWindow = Window & {
  desktopApp?: { isDesktop?: boolean }
}

const isDesktopPlaybackClient = () => {
  if (typeof window === 'undefined') return false
  const desktopWindow = window as DesktopWindow
  if (desktopWindow.desktopApp?.isDesktop === true) return true
  if (typeof navigator === 'undefined') return false
  return /electron|tauri/i.test(String(navigator.userAgent || ''))
}

// Derive the presentation facts (title / uploader) from a video. Mirrors the
// derivation the shell's 16-source watcher used to do inline; now it lives next
// to the owner so the watcher doesn't have to.
const firstProfile = (video: VideoPageVideo | null): VideoProfile | null => {
  const subs = video?.subscriptions
  if (Array.isArray(subs) && subs.length) return subs[0] || null
  const actors = video?.actors
  if (Array.isArray(actors) && actors.length) return actors[0] || null
  return null
}

const derivePresentation = (video: VideoPageVideo | null) => {
  const primaryProfile = firstProfile(video)
  const uploader = String(
    primaryProfile?.name
    || video?.uploader
    || video?.uploader_name
    || ''
  )
  const title = String(video?.title || '')
  return { title, uploader }
}

export default function usePlaybackOrchestrator() {
  const session = usePlaybackSession()
  const { video, startTime, fetchVideoDetails, maybeInjectSubtitles, setVideoSnapshot } = useVideoDetail(session)
  const { relatedVideos, loadingRelated, fetchRelatedVideos } = useRelatedVideos(session, video)
  const { getPlaybackSource } = useVideoOperations()

  // Projections — read-only views of the single owner. There are no local refs
  // for these facts anymore.
  const playbackSource = computed(() => session.facts.source)
  const subtitleTracks = computed(() => session.facts.subtitles)
  const externalError = computed(() => session.facts.externalError)
  const isResolvingPlayback = computed(() => session.facts.externalLoading)
  // Stale-closure guard for superseded fetches. Plain counter (not a ref): it
  // is never read reactively — only compared inside loadAndPlayById's async
  // branches. Matches the idiom in useRelatedVideos.
  let requestSeq = 0

  const loadAndPlayById = async (
    videoId: VideoId,
    initialVideoData: VideoPageVideo | null = null,
    options: PlayOptions = {}
  ) => {
    if (!videoId) return

    requestSeq += 1
    const seq = requestSeq

    Logger.debug('[usePlaybackOrchestrator] loadAndPlayById start', { videoId, seq })

    // Begin a fresh session for this video. This clears stale source / video /
    // externalError and marks externalLoading. `initialVideoData` seeds the
    // video fact so subsequent reads (uploader / title / detail dedupe) resolve
    // synchronously.
    session.beginNewVideo(String(videoId), initialVideoData)

    const currentVideoId = session.facts.video?.id != null ? String(session.facts.video.id) : ''
    const targetVideoId = String(videoId)

    if (initialVideoData && initialVideoData.id === videoId) {
      setVideoSnapshot(initialVideoData)
    }
    if (!initialVideoData && currentVideoId && currentVideoId !== targetVideoId) {
      setVideoSnapshot(null)
    }

    const hasInitialData = !!session.facts.video && session.facts.video.id === videoId
    const detailPromise = !hasInitialData
      ? fetchVideoDetails(videoId).catch((e) => {
          Logger.error('[usePlaybackOrchestrator] fetchVideoDetails error', e)
          return null
        })
      : fetchVideoDetails(videoId).catch((e) => {
          Logger.error('[usePlaybackOrchestrator] fetchVideoDetails error', e)
          return null
        })
    const playbackPromise = (async () => {
      const initialPlaybackVideo = (() => {
        if (initialVideoData && typeof initialVideoData.url === 'string') {
          return initialVideoData
        }
        if (hasInitialData && typeof session.facts.video?.url === 'string') {
          return session.facts.video
        }
        return null
      })()

      if (initialPlaybackVideo) {
        return getPlaybackSource(videoId, options, initialPlaybackVideo)
      }

      if (isDesktopPlaybackClient()) {
        const detailedVideo = await detailPromise
        if (detailedVideo && typeof detailedVideo.url === 'string') {
          return getPlaybackSource(videoId, options, detailedVideo)
        }
      }

      return getPlaybackSource(videoId, options, null)
    })()

    Promise.resolve(detailPromise).then(() => {
      Logger.debug('[usePlaybackOrchestrator] after fetchVideoDetails', {
        hasVideo: !!session.facts.video,
      })
      if (seq !== requestSeq) return

      maybeInjectSubtitles(videoId).catch((e) =>
        Logger.error('[usePlaybackOrchestrator] maybeInjectSubtitles error', e)
      )
      fetchRelatedVideos(videoId).catch((e) =>
        Logger.error('[usePlaybackOrchestrator] fetchRelatedVideos error', e)
      )
    })

    try {
      const source = await playbackPromise
      await detailPromise
      if (seq !== requestSeq) return

      const v = session.facts.video || initialVideoData || null
      const sourceMetadata = 'metadata' in source ? source.metadata : undefined
      const mergedVideo = mergePlaybackMetadata(v, toRecord(sourceMetadata))
      if (mergedVideo && mergedVideo !== session.facts.video) {
        setVideoSnapshot(mergedVideo)
      }
      const resolvedSource: MediaSource = {
        ...source,
        title: source.title || mergedVideo?.title || v?.title || '',
      }

      // Forward the resolved source + presentation projection in a single
      // update. externalLoading is flipped false by the `finally` below (single
      // point), matching the old orchestrator's success path.
      session.update({
        source: resolvedSource,
        ...derivePresentation(session.facts.video),
      })

      Logger.debug('[usePlaybackOrchestrator] playbackSource ready', {
        videoId,
        src: session.facts.source?.src,
      })
    } catch (err) {
      if (seq !== requestSeq) return

      const e = toRecord(err)
      const code = String(e.code || 'FAILED')
      const message = String(e.message || '播放链接获取失败')
      session.update({
        externalError: {
          code,
          title: '播放失败',
          message,
          canRetry: true,
        },
      })
    } finally {
      if (seq === requestSeq) {
        session.update({ externalLoading: false })
      }
    }
  }

  const toSubtitleTracks = (subtitles: unknown): SubtitleTrack[] => {
    if (!Array.isArray(subtitles)) return []

    return subtitles.map((item, i) => {
      const s = toRecord(item)
      const id = String(s.id || `sub-${i}`)
      const language = String(s.language || s.lang || 'unknown')
      const label = String(s.label || s.name || language || `Subtitle ${i + 1}`)
      const url = typeof s.url === 'string'
        ? s.url
        : (typeof s.src === 'string' ? s.src : undefined)
      const content = typeof s.content === 'string' ? s.content : undefined
      const isDefault = s.default === true

      return {
        id,
        label,
        language,
        url,
        content,
        default: isDefault || (!subtitles.some((x) => toRecord(x).default === true) && i === 0),
      }
    })
  }

  // When the session video gains subtitle candidates (either from the detail
  // fetch or from useVideoDetail's desktop subtitle injection), project them
  // into facts.subtitles. This replaces the old local ref that the shell's
  // watcher reconciled.
  watch(
    () => session.facts.video?.subtitles,
    (subtitles) => {
      session.update({ subtitles: toSubtitleTracks(subtitles) })
    },
    { immediate: true, deep: true }
  )

  // Forward initialTime whenever the video identity (and thus startTime)
  // changes. The shell used to read startTime via resolvedInitialTime and pump
  // it through the watcher; now the orchestrator writes it directly.
  watch(startTime, (t) => {
    session.update({ initialTime: t })
  }, { immediate: true })

  // Keep the presentation projection (title / uploader) in sync with the video
  // fact. This is the derivation the shell's watcher used to inline.
  watch(() => session.facts.video, (videoFact) => {
    session.update(derivePresentation(videoFact))
  }, { immediate: true })

  return {
    // state — all read-only projections of session.facts
    video,
    startTime,
    relatedVideos,
    loadingRelated,
    playbackSource,
    subtitleTracks,
    externalError,
    isResolvingPlayback,

    // actions
    loadAndPlayById,
  }
}
