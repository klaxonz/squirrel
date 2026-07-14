import { computed } from 'vue'
import type { ComputedRef } from 'vue'

import { getVideoList } from '@/shared/api'
import type { VideoId, VideoPageVideo } from '@/features/playback/types/videoPlayback'
import type { PlaybackSession } from '@/features/playback/composables/usePlaybackSession'

type VideoListResponse = { data?: unknown[] }

// ADR-0002 PR2 — `relatedVideos` / `loadingRelated` were local refs.
// They are now computed projections of PlaybackSession.facts (single owner);
// fetch results call session.update instead of mutating local refs.
export default function useRelatedVideos(session: PlaybackSession, sourceVideo: ComputedRef<VideoPageVideo | null>) {
  const relatedVideos = computed(() => session.facts.relatedVideos)
  const loadingRelated = computed(() => session.facts.loadingRelated)
  let requestSeq = 0

  const extractItems = (videos: VideoListResponse | null | undefined) => (Array.isArray(videos?.data) ? videos!.data! : [])

  // Collect up to `pageSize` related videos, preferring same-subscription then
  // same-site. Each sub-fetch is isolated so one failing source doesn't abort
  // the whole collection — a failed source just contributes nothing.
  const collectRelated = async (video: VideoPageVideo, { pageSize = 20 }: { pageSize?: number } = {}): Promise<VideoPageVideo[]> => {
    if (!video) return []

    const collected: VideoPageVideo[] = []

    const primarySubId = video?.subscriptions?.[0]?.id
    if (primarySubId) {
      try {
        const data = await getVideoList({
          pageSize,
          sort_by: 'publish_date',
          subscription_id: primarySubId,
        })
        collected.push(...(extractItems(data) as VideoPageVideo[]))
      } catch {
        // primary source unavailable — fall through to site-wide
      }
    }

    if (collected.length < pageSize && video?.site) {
      const remaining = pageSize - collected.length
      try {
        const data = await getVideoList({
          pageSize: remaining,
          sort_by: 'publish_date',
          site: video.site,
        })
        collected.push(...(extractItems(data) as VideoPageVideo[]))
      } catch {
        // site-wide source also unavailable — keep whatever primary gave us
      }
    }

    const unique: VideoPageVideo[] = []
    const seen = new Set<VideoId>()
    for (const item of collected) {
      if (!item || item.id === video.id) continue
      const itemId = item.id
      if (itemId == null) continue
      if (seen.has(itemId)) continue
      seen.add(itemId)
      unique.push(item)
      if (unique.length >= pageSize) break
    }

    return unique
  }

  const fetchRelatedVideos = async (expectedVideoId?: VideoId) => {
    const snapshot = sourceVideo.value
    if (!snapshot) return

    const expectedId = expectedVideoId !== undefined ? String(expectedVideoId) : String(snapshot.id)
    if (String(snapshot.id) !== expectedId) return

    requestSeq += 1
    const seq = requestSeq

    session.update({ relatedVideos: [], loadingRelated: true })
    try {
      const data = await collectRelated(snapshot, { pageSize: 20 })
      if (seq !== requestSeq) return
      if (String(sourceVideo.value?.id) !== expectedId) return
      session.update({ relatedVideos: data })
    } catch {
      if (seq === requestSeq) session.update({ relatedVideos: [] })
    } finally {
      if (seq === requestSeq) {
        session.update({ loadingRelated: false })
      }
    }
  }

  const setRelatedVideosSnapshot = (items: VideoPageVideo[] = [], loading = false) => {
    requestSeq += 1
    session.update({
      relatedVideos: Array.isArray(items) ? [...items] : [],
      loadingRelated: !!loading,
    })
  }

  return {
    relatedVideos,
    loadingRelated,
    fetchRelatedVideos,
    setRelatedVideosSnapshot,
  }
}
