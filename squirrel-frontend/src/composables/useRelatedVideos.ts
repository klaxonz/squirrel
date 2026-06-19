import { computed } from 'vue'
import type { ComputedRef } from 'vue'

import { getVideoList } from '@/api'
import type { VideoId, VideoPageVideo } from '@/types/videoPlayback'
import type { PlaybackSession } from '@/composables/usePlaybackSession'

type VideoListResponse = { data?: unknown[] }

// ADR-0002 PR2 — `relatedVideos` / `loadingRelated` were local refs.
// They are now computed projections of PlaybackSession.facts (single owner);
// fetch results call session.update instead of mutating local refs.
export default function useRelatedVideos(session: PlaybackSession, sourceVideo: ComputedRef<VideoPageVideo | null>) {
  const relatedVideos = computed(() => session.facts.relatedVideos)
  const loadingRelated = computed(() => session.facts.loadingRelated)
  let requestSeq = 0

  const extractItems = (videos: VideoListResponse | null | undefined) => (Array.isArray(videos?.data) ? videos!.data! : [])

  const getRelatedVideos = async (video: VideoPageVideo, { pageSize = 20 }: { pageSize?: number } = {}) => {
    if (!video) return { data: [] as VideoPageVideo[], error: null as unknown | null }

    const collected: VideoPageVideo[] = []

    const primarySubId = video?.subscriptions?.[0]?.id
    if (primarySubId) {
      const { data, error } = await getVideoList({
        pageSize,
        sort_by: 'publish_date',
        subscription_id: primarySubId,
      })
      if (!error) collected.push(...(extractItems(data) as VideoPageVideo[]))
    }

    if (collected.length < pageSize && video?.site) {
      const remaining = pageSize - collected.length
      const { data, error } = await getVideoList({
        pageSize: remaining,
        sort_by: 'publish_date',
        site: video.site,
      })
      if (!error) collected.push(...(extractItems(data) as VideoPageVideo[]))
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

    return { data: unique, error: null as unknown | null }
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
      const { data, error } = await getRelatedVideos(snapshot, { pageSize: 20 })
      if (seq !== requestSeq) return
      if (String(sourceVideo.value?.id) !== expectedId) return
      session.update({ relatedVideos: !error ? data || [] : [] })
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
