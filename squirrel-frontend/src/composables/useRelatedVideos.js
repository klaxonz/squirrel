import { ref } from 'vue'
import { getVideoList } from '@/api'

export default function useRelatedVideos(sourceVideo) {
  const relatedVideos = ref([])
  const loadingRelated = ref(false)

  const extractItems = (data) => (Array.isArray(data?.data) ? data.data : [])

  const getRelatedVideos = async (video, { pageSize = 20 } = {}) => {
    if (!video) return { data: [], error: null }

    const collected = []

    const primarySubId = video?.subscriptions?.[0]?.id
    if (primarySubId) {
      const { data, error } = await getVideoList({
        page: 1,
        pageSize,
        sort_by: 'publish_date',
        subscription_id: primarySubId,
      })
      if (!error) collected.push(...extractItems(data))
    }

    if (collected.length < pageSize && video?.site) {
      const remaining = pageSize - collected.length
      const { data, error } = await getVideoList({
        page: 1,
        pageSize: remaining,
        sort_by: 'publish_date',
        site: video.site,
      })
      if (!error) collected.push(...extractItems(data))
    }

    const unique = []
    const seen = new Set()
    for (const item of collected) {
      if (!item || item.id === video.id) continue
      if (seen.has(item.id)) continue
      seen.add(item.id)
      unique.push(item)
      if (unique.length >= pageSize) break
    }

    return { data: unique, error: null }
  }

  const fetchRelatedVideos = async () => {
    if (!sourceVideo.value) return
    loadingRelated.value = true
    try {
      const { data, error } = await getRelatedVideos(sourceVideo.value, { pageSize: 20 })
      relatedVideos.value = !error ? (data || []) : []
    } finally {
      loadingRelated.value = false
    }
  }

  return {
    relatedVideos,
    loadingRelated,
    fetchRelatedVideos,
  }
}


