import { ref } from 'vue'
import type { Ref } from 'vue'
import { getVideoList } from '@/api'
import type { ApiResult, VideoId, VideoPageVideo } from '@/types/videoPlayback'

type VideoListResponse = { data?: unknown[] }

export default function useRelatedVideos(sourceVideo: Ref<VideoPageVideo | null>) {
  const relatedVideos = ref<VideoPageVideo[]>([])
  const loadingRelated = ref(false)
  const requestSeq = ref(0)

  const extractItems = (videos: VideoListResponse | null | undefined) => (Array.isArray(videos?.data) ? videos!.data! : [])

  const getRelatedVideos = async (video: VideoPageVideo, { pageSize = 20 }: { pageSize?: number } = {}) => {
    if (!video) return { data: [] as VideoPageVideo[], error: null as unknown | null }

    const collected: VideoPageVideo[] = []

    const primarySubId = video?.subscriptions?.[0]?.id
    if (primarySubId) {
      const { data, error } = (await getVideoList({
        pageSize,
        sort_by: 'publish_date',
        subscription_id: primarySubId,
      })) as ApiResult<VideoListResponse>
      if (!error) collected.push(...(extractItems(data) as VideoPageVideo[]))
    }

    if (collected.length < pageSize && video?.site) {
      const remaining = pageSize - collected.length
      const { data, error } = (await getVideoList({
        pageSize: remaining,
        sort_by: 'publish_date',
        site: video.site,
      })) as ApiResult<VideoListResponse>
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

    requestSeq.value += 1
    const seq = requestSeq.value

    relatedVideos.value = []
    loadingRelated.value = true
    try {
      const { data, error } = await getRelatedVideos(snapshot, { pageSize: 20 })
      if (seq !== requestSeq.value) return
      if (String(sourceVideo.value?.id) !== expectedId) return
      relatedVideos.value = !error ? data || [] : []
    } finally {
      if (seq === requestSeq.value) {
        loadingRelated.value = false
      }
    }
  }

  const setRelatedVideosSnapshot = (items: VideoPageVideo[] = [], loading = false) => {
    requestSeq.value += 1
    relatedVideos.value = Array.isArray(items) ? [...items] : []
    loadingRelated.value = !!loading
  }

  return {
    relatedVideos,
    loadingRelated,
    fetchRelatedVideos,
    setRelatedVideosSnapshot,
  }
}


