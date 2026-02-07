import { ref } from 'vue'
import type { Ref } from 'vue'
import { getVideoList } from '@/api'

type VideoId = string | number

type VideoListItem = {
  id: VideoId
  subscriptions?: Array<{ id?: VideoId }>
  site?: string
  [key: string]: unknown
}

type ApiResult<T> = { data?: T | null; error?: unknown | null }
type VideoListResponse = { data?: unknown[] }

export default function useRelatedVideos(sourceVideo: Ref<VideoListItem | null>) {
  const relatedVideos = ref<VideoListItem[]>([])
  const loadingRelated = ref(false)
  const requestSeq = ref(0)

  const extractItems = (data: VideoListResponse | null | undefined) => (Array.isArray(data?.data) ? data!.data! : [])

  const getRelatedVideos = async (video: VideoListItem, { pageSize = 20 }: { pageSize?: number } = {}) => {
    if (!video) return { data: [] as VideoListItem[], error: null as unknown | null }

    const collected: VideoListItem[] = []

    const primarySubId = video?.subscriptions?.[0]?.id
    if (primarySubId) {
      const { data, error } = (await getVideoList({
        page: 1,
        pageSize,
        sort_by: 'publish_date',
        subscription_id: primarySubId,
      })) as ApiResult<VideoListResponse>
      if (!error) collected.push(...(extractItems(data) as any))
    }

    if (collected.length < pageSize && video?.site) {
      const remaining = pageSize - collected.length
      const { data, error } = (await getVideoList({
        page: 1,
        pageSize: remaining,
        sort_by: 'publish_date',
        site: video.site,
      })) as ApiResult<VideoListResponse>
      if (!error) collected.push(...(extractItems(data) as any))
    }

    const unique: VideoListItem[] = []
    const seen = new Set<VideoId>()
    for (const item of collected) {
      if (!item || item.id === video.id) continue
      if (seen.has(item.id)) continue
      seen.add(item.id)
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

  return {
    relatedVideos,
    loadingRelated,
    fetchRelatedVideos,
  }
}


