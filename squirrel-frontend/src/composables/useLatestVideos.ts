import { computed, shallowRef, ref } from 'vue'
import { getVideoList } from '@/api'

type VideoId = string | number

type VideoListItem = {
  id: VideoId
  is_read?: boolean
  isPlaying?: boolean
  video_url?: string | null
  [key: string]: unknown
}

type InitialState = {
  activeTab?: string
  searchQuery?: string
  subscriptionId?: VideoId | null
  sortBy?: string
  nsfw?: string
  site?: string
  timeRange?: string
  duration?: string
  contentType?: string
}

type ApiResult<T> = { data?: T | null; error?: unknown | null }
type VideoListResponse = { data?: unknown[] }
type ApiErrorLike = { type?: string | null }

export default function useLatestVideos(initial: InitialState = {}) {
  const videos = shallowRef<VideoListItem[]>([])
  const loading = ref(false)
  const allLoaded = ref(false)
  const error = ref<unknown | null>(null)
  const activeTab = ref(initial.activeTab ?? 'unread')
  const currentPage = ref(1)
  const searchQuery = ref(initial.searchQuery ?? '')
  const isResetting = ref(false)
  const subscriptionId = ref<VideoId | null>(initial.subscriptionId ?? null)
  const sortBy = ref(initial.sortBy ?? 'publish_date')
  const nsfw = ref(initial.nsfw ?? 'all')
  const site = ref<string | undefined>(initial.site)
  const timeRange = ref(initial.timeRange ?? 'all')
  const duration = ref(initial.duration ?? 'all')
  const contentType = ref(initial.contentType ?? 'all')

  const category = computed(() => activeTab.value)

  let requestToken = 0
  let listAbortController: AbortController | null = null

  const loadMore = async () => {
    if (loading.value || allLoaded.value) return
    loading.value = true

    const pageSize = 50
    const currentToken = ++requestToken
    listAbortController?.abort()
    listAbortController = new AbortController()

    const { data, error: requestError } = (await getVideoList({
      page: currentPage.value,
      pageSize,
      query: searchQuery.value || '',
      subscription_id: subscriptionId.value,
      category: category.value,
      sort_by: sortBy.value,
      nsfw: nsfw.value,
      site: site.value,
      time_range: timeRange.value,
      duration: duration.value,
      content_type: contentType.value,
    }, {
      signal: listAbortController.signal,
    })) as ApiResult<VideoListResponse>

    if (currentToken !== requestToken) {
      loading.value = false
      return
    }

    if ((requestError as ApiErrorLike | null)?.type === 'CANCELED') {
      loading.value = false
      return
    }

    if (requestError) {
      error.value = requestError
      loading.value = false
      return
    }

    const rawList = Array.isArray(data?.data) ? data?.data : []
    const newVideos: VideoListItem[] = rawList.map((video: any) => ({
      ...video,
      is_read: video?.is_read ?? false,
      isPlaying: false,
      video_url: null,
    }))

    if (currentPage.value === 1) {
      const seen = new Set<VideoId>()
      const deduped = newVideos.filter((video) => {
        if (seen.has(video.id)) return false
        seen.add(video.id)
        return true
      })
      videos.value = deduped
    } else {
      const existingIds = new Set(videos.value.map((v) => v.id))
      const uniqueNewVideos = newVideos.filter((video) => !existingIds.has(video.id))
      videos.value = [...videos.value, ...uniqueNewVideos]
    }

    currentPage.value++
    allLoaded.value = newVideos.length < pageSize
    loading.value = false
  }

  const resetAndReload = async () => {
    isResetting.value = true
    currentPage.value = 1
    allLoaded.value = false
    error.value = null
    try {
      await loadMore()
    } finally {
      isResetting.value = false
    }
  }

  return {
    videos,
    loading,
    allLoaded,
    error,
    activeTab,
    handleSearch: resetAndReload,
    refresh: resetAndReload,
    loadMore,
    searchQuery,
    subscriptionId,
    sortBy,
    nsfw,
    site,
    timeRange,
    duration,
    contentType,
    isResetting,
  }
}
